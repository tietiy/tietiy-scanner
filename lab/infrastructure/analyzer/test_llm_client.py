"""
Unit tests for analyzer/llm_client.py.

Run:
    .venv/bin/python -m pytest lab/infrastructure/analyzer/test_llm_client.py -v
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_client import (  # noqa: E402
    LLMClient, LLMResponse, _hash_input, _mechanism_prompt,
    _load_dotenv_if_needed, _PRICE_INPUT_PER_M, _PRICE_OUTPUT_PER_M,
)


# ── _hash_input determinism ───────────────────────────────────────────

def test_hash_input_deterministic():
    a = _hash_input({"x": 1, "y": "z"})
    b = _hash_input({"y": "z", "x": 1})  # different dict order
    assert a == b


def test_hash_input_distinct_for_diff_input():
    a = _hash_input({"x": 1})
    b = _hash_input({"x": 2})
    assert a != b


# ── _mechanism_prompt content ────────────────────────────────────────

def test_mechanism_prompt_includes_features_and_evidence():
    pattern = {
        "cohort": {"signal_type": "UP_TRI", "regime": "Bear", "horizon": "D10"},
        "features": [
            {"feature_id": "ema_alignment", "level": "bull"},
            {"feature_id": "RSI_14", "level": "high"},
        ],
        "statistical_evidence": {
            "lifetime_n_test": 33, "lifetime_test_wr": 0.85,
            "lifetime_baseline_wr": 0.54, "lifetime_edge_pp": 31.0,
            "lifetime_drift": 7.5,
        },
    }
    p = _mechanism_prompt(pattern)
    assert "UP_TRI" in p and "Bear" in p and "D10" in p
    assert "ema_alignment=bull" in p
    assert "RSI_14=high" in p
    assert "33" in p
    assert "JSON" in p


# ── _load_dotenv_if_needed ───────────────────────────────────────────

def test_dotenv_loader_populates_env(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # Patch repo root to tmp
    fake_env = tmp_path / ".env"
    fake_env.write_text("ANTHROPIC_API_KEY=sk-test-mock-key\nOTHER=1\n")
    import llm_client as mod
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
    _load_dotenv_if_needed()
    assert os.getenv("ANTHROPIC_API_KEY") == "sk-test-mock-key"


# ── LLMClient cache hit ───────────────────────────────────────────────

def test_cache_hit_returns_cached_response(tmp_path, monkeypatch):
    """If the cache key file already exists, generate_mechanism returns it
    without making an API call."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-mock-key")
    pattern = {
        "cohort": {"signal_type": "UP_TRI", "regime": "Bear", "horizon": "D10"},
        "features": [{"feature_id": "ema_alignment", "level": "bull"}],
        "statistical_evidence": {
            "lifetime_n_test": 33, "lifetime_test_wr": 0.85,
            "lifetime_baseline_wr": 0.54, "lifetime_edge_pp": 31.0,
            "lifetime_drift": 7.5,
        },
    }
    cache_dir = tmp_path / "llm_cache"
    cache_dir.mkdir()
    # Pre-populate cache file
    from llm_client import DEFAULT_MODEL
    key = _hash_input({"prompt": "mechanism_v1", "data": pattern,
                          "model": DEFAULT_MODEL})
    (cache_dir / f"{key}.json").write_text(json.dumps({
        "mechanism": "Cached mechanism string.",
        "concept": "trend_continuation",
        "clarity": 75,
    }))
    # Mock anthropic so we don't accidentally hit real API
    with patch("llm_client.LLMClient._call_with_retry") as mock_call:
        client = LLMClient(cache_dir=cache_dir)
        result = client.generate_mechanism(pattern)
        assert result.cached
        assert result.mechanism == "Cached mechanism string."
        assert result.concept == "trend_continuation"
        assert result.clarity == 75
        mock_call.assert_not_called()


# ── LLMClient parses JSON robustly ────────────────────────────────────

def test_parse_json_handles_markdown_fence():
    text = "```json\n{\"mechanism\": \"x\", \"concept\": \"y\", \"clarity\": 50}\n```"
    parsed = LLMClient._parse_json(text)
    assert parsed["mechanism"] == "x"
    assert parsed["clarity"] == 50


def test_parse_json_handles_surrounding_prose():
    text = "Here is the answer: {\"mechanism\": \"x\", \"concept\": null, \"clarity\": 30}\nDone."
    parsed = LLMClient._parse_json(text)
    assert parsed["mechanism"] == "x"


def test_parse_json_returns_unclear_on_garbage():
    parsed = LLMClient._parse_json("nonsense without braces")
    assert "unclear" in parsed["mechanism"]
    assert parsed["clarity"] == 0


# ── Cost tracking ────────────────────────────────────────────────────

def test_cost_tracking_accumulates(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-mock-key")
    cache_dir = tmp_path / "llm_cache"
    pattern = {
        "cohort": {"signal_type": "UP_TRI", "regime": "Bear", "horizon": "D10"},
        "features": [{"feature_id": "ema_alignment", "level": "bull"}],
        "statistical_evidence": {"lifetime_n_test": 33, "lifetime_test_wr": 0.85},
    }
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text='{"mechanism":"m","concept":"c","clarity":80}')]
    fake_msg.usage = MagicMock(input_tokens=100, output_tokens=50)

    with patch("llm_client.LLMClient.__init__", lambda self, **kw: None):
        client = LLMClient.__new__(LLMClient)
        # Manual init
        client._client = MagicMock()
        client._client.messages.create.return_value = fake_msg
        client.model = "claude-sonnet-4-5-20250929"
        client.cache_dir = cache_dir
        client.cache_dir.mkdir(parents=True, exist_ok=True)
        client.max_concurrent = 5
        client._total_cost = 0.0
        client._total_calls = 0
        client._cache_hits = 0
        result = client.generate_mechanism(pattern)
        # Expected cost: 100/1M * 3 + 50/1M * 15 = 0.0003 + 0.00075 = 0.00105
        expected_cost = (100 * _PRICE_INPUT_PER_M / 1_000_000.0
                          + 50 * _PRICE_OUTPUT_PER_M / 1_000_000.0)
        assert abs(client.total_cost - expected_cost) < 1e-9
        assert client.total_calls == 1
        assert result.clarity == 80


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
