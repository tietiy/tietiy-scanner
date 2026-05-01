"""
Centralized Anthropic Claude API wrapper for analyzer.

Features:
  • Disk cache (lab/cache/llm/) keyed on sha256 of input
  • Retry with exponential backoff on rate-limit / transient errors (3 attempts)
  • Concurrency cap (max 5 in-flight requests)
  • Cost tracking → lab/cache/llm/cost_log.jsonl
  • Loads ANTHROPIC_API_KEY from env or repo-root .env

Mechanism prompt format (single-step):
  Pattern + sample evidence → JSON {mechanism, concept, clarity}

NO production scanner modifications. Lab-only.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
_REPO_ROOT = _LAB_ROOT.parent

CACHE_DIR = _LAB_ROOT / "cache" / "llm"
COST_LOG = CACHE_DIR / "cost_log.jsonl"

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"  # Sonnet 4.5; 4.6 alias may not exist in SDK 0.97
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.5
MAX_CONCURRENT = 5

# Sonnet 4.5 pricing (as of 2026): $3 per million input tokens, $15 per million output
_PRICE_INPUT_PER_M = 3.0
_PRICE_OUTPUT_PER_M = 15.0


def _load_dotenv_if_needed() -> None:
    """If ANTHROPIC_API_KEY not in env, load from repo-root .env file."""
    if os.getenv("ANTHROPIC_API_KEY"):
        return
    env_path = _REPO_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                os.environ.setdefault(k, v)
    except Exception:
        pass


def _hash_input(payload: dict) -> str:
    """Deterministic sha256 of dict (sort_keys for stability)."""
    s = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(s.encode()).hexdigest()


@dataclass
class LLMResponse:
    """Parsed mechanism response."""
    mechanism: str
    concept: Optional[str]
    clarity: int
    cached: bool
    input_tokens: int
    output_tokens: int
    cost_usd: float


def _mechanism_prompt(pattern_data: dict) -> str:
    """Build the single-step mechanism prompt per spec."""
    cohort = pattern_data.get("cohort", {})
    features = pattern_data.get("features", [])
    stat = pattern_data.get("statistical_evidence", {})
    feature_lines = "\n".join(
        f"  - {f.get('feature_id')}={f.get('level')}" for f in features)
    return f"""Pattern: {cohort.get('signal_type')} × {cohort.get('regime')} × {cohort.get('horizon')} cohort.
Features:
{feature_lines}

Sample evidence:
- Lifetime n_test: {stat.get('lifetime_n_test')}
- Lifetime test WR: {stat.get('lifetime_test_wr')}
- Cohort baseline WR: {stat.get('lifetime_baseline_wr')}
- Edge over baseline: {stat.get('lifetime_edge_pp')}pp
- Walk-forward drift (train→test): {stat.get('lifetime_drift')}pp

Task: Generate a mechanism explanation for why this pattern produces edge.

Requirements:
- 2 sentences maximum
- Use trader-friendly language (not jargon-heavy)
- Reference established market concepts where applicable:
  institutional_accumulation, sector_rotation, mean_reversion,
  trend_continuation, regime_transition, calendar_flow,
  weak_hands_capitulation, smart_money_positioning
- If no clear mechanism exists, explicitly say "unclear mechanism"
- Don't invent mechanisms to fit; honest "unclear" preferred to fabricated

Then assess clarity (0-100):
- 80-100: Cites established concept, mechanism logically follows from features
- 50-79: Plausible but generic
- 20-49: Reach explanation, mechanism unclear
- 0-19: No clear mechanism, possibly statistical artifact

Return ONLY a JSON object (no surrounding prose, no markdown fences):
{{"mechanism": "<2-sentence explanation>", "concept": "<concept_name or null>", "clarity": <0-100>}}"""


class LLMClient:
    """Thin wrapper over anthropic.Anthropic with cache + retry + cost log."""

    def __init__(self,
                 model: str = DEFAULT_MODEL,
                 cache_dir: Path = CACHE_DIR,
                 max_concurrent: int = MAX_CONCURRENT):
        _load_dotenv_if_needed()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set; populate env or .env file")
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise RuntimeError(
                f"anthropic SDK required; install with pip: {e}")
        self._client = Anthropic(api_key=api_key)
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent
        self._total_cost = 0.0
        self._total_calls = 0
        self._cache_hits = 0

    # ── Mechanism generation ─────────────────────────────────────────

    def generate_mechanism(self, pattern_data: dict) -> LLMResponse:
        """Single mechanism generation; uses cache if available."""
        key = _hash_input({"prompt": "mechanism_v1", "data": pattern_data,
                              "model": self.model})
        cache_path = self.cache_dir / f"{key}.json"
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text())
                self._cache_hits += 1
                return LLMResponse(
                    mechanism=cached["mechanism"],
                    concept=cached.get("concept"),
                    clarity=int(cached["clarity"]),
                    cached=True,
                    input_tokens=cached.get("input_tokens", 0),
                    output_tokens=cached.get("output_tokens", 0),
                    cost_usd=0.0,  # cached calls cost nothing
                )
            except Exception:
                pass  # corrupt cache; refetch

        prompt = _mechanism_prompt(pattern_data)
        result = self._call_with_retry(prompt)
        # Persist to cache
        try:
            cache_path.write_text(json.dumps({
                "mechanism": result.mechanism,
                "concept": result.concept,
                "clarity": result.clarity,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            }, indent=2))
        except Exception:
            pass
        return result

    def batch_generate_mechanisms(self,
                                       patterns: list[dict],
                                       progress_every: int = 10
                                       ) -> list[LLMResponse]:
        """Concurrent mechanism generation with a thread pool of size
        max_concurrent. Order preserved."""
        results: list[Optional[LLMResponse]] = [None] * len(patterns)
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as pool:
            futures = {pool.submit(self.generate_mechanism, p): i
                          for i, p in enumerate(patterns)}
            done = 0
            for f in as_completed(futures):
                i = futures[f]
                try:
                    results[i] = f.result()
                except Exception as e:  # noqa: BLE001
                    print(f"  pattern {i} mechanism failed: {e}",
                          file=sys.stderr)
                    results[i] = LLMResponse(
                        mechanism=f"ERROR: {e}",
                        concept=None, clarity=0, cached=False,
                        input_tokens=0, output_tokens=0, cost_usd=0.0,
                    )
                done += 1
                if done % progress_every == 0:
                    print(f"  mechanism {done}/{len(patterns)} "
                          f"(cache_hits={self._cache_hits}, "
                          f"cost=${self._total_cost:.3f})",
                          file=sys.stderr)
        return [r for r in results if r is not None]

    # ── Single-call findings synthesis ────────────────────────────────

    def synthesize_findings(self, prompt: str,
                                max_tokens: int = 4000) -> str:
        """One-shot text generation for human-readable findings doc.
        No cache (each run produces a unique synthesis)."""
        result = self._call_with_retry(prompt, max_tokens=max_tokens,
                                            parse_json=False)
        return result.mechanism  # we reuse the field for raw text

    # ── Internals ─────────────────────────────────────────────────────

    def _call_with_retry(self, prompt: str, max_tokens: int = 600,
                            parse_json: bool = True) -> LLMResponse:
        """Single API call with exponential backoff retry."""
        from anthropic import APIError, RateLimitError, APIConnectionError

        backoff = INITIAL_BACKOFF
        last_err: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                msg = self._client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                # Extract text
                text = "".join(
                    blk.text for blk in msg.content if hasattr(blk, "text"))
                input_tok = msg.usage.input_tokens
                output_tok = msg.usage.output_tokens
                cost = (input_tok * _PRICE_INPUT_PER_M / 1_000_000.0
                         + output_tok * _PRICE_OUTPUT_PER_M / 1_000_000.0)
                self._total_cost += cost
                self._total_calls += 1
                self._log_cost(input_tok, output_tok, cost)

                if parse_json:
                    parsed = self._parse_json(text)
                    return LLMResponse(
                        mechanism=parsed.get("mechanism", "unclear"),
                        concept=parsed.get("concept"),
                        clarity=int(parsed.get("clarity", 0)),
                        cached=False,
                        input_tokens=input_tok,
                        output_tokens=output_tok,
                        cost_usd=cost,
                    )
                else:
                    return LLMResponse(
                        mechanism=text, concept=None, clarity=0,
                        cached=False, input_tokens=input_tok,
                        output_tokens=output_tok, cost_usd=cost,
                    )
            except (RateLimitError, APIConnectionError) as e:
                last_err = e
                wait = backoff * (attempt + 1)
                print(f"  retry {attempt+1}/{MAX_RETRIES} after {wait:.1f}s "
                      f"(rate limit / connection): {e}", file=sys.stderr)
                time.sleep(wait)
                backoff *= 2
            except APIError as e:
                last_err = e
                wait = backoff
                print(f"  retry {attempt+1}/{MAX_RETRIES} after {wait:.1f}s "
                      f"(API error): {e}", file=sys.stderr)
                time.sleep(wait)
                backoff *= 2
            except Exception as e:  # noqa: BLE001
                last_err = e
                break  # don't retry unexpected errors

        raise RuntimeError(
            f"LLM call failed after {MAX_RETRIES} attempts: {last_err}")

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Extract JSON object from LLM response, tolerant to surrounding prose."""
        text = text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            inner = [l for l in lines if not l.startswith("```")]
            text = "\n".join(inner)
        # Find first { ... } block
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < 0:
            return {"mechanism": "unclear (parse error)", "concept": None, "clarity": 0}
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return {"mechanism": "unclear (parse error)", "concept": None, "clarity": 0}

    def _log_cost(self, input_tok: int, output_tok: int, cost: float) -> None:
        try:
            with open(COST_LOG, "a") as fh:
                fh.write(json.dumps({
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "model": self.model,
                    "input_tokens": input_tok,
                    "output_tokens": output_tok,
                    "cost_usd": cost,
                }) + "\n")
        except Exception:
            pass

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def total_calls(self) -> int:
        return self._total_calls

    @property
    def cache_hits(self) -> int:
        return self._cache_hits
