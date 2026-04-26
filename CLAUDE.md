# CLAUDE.md — TIE TIY Scanner — Operating Conventions

**Read this first every session.** Seven conventions, not principles. Violating these has cost time before — written down so it doesn't repeat.

---

## 1. Python interpreter

**Always use `.venv/bin/python`** — never bare `python` (doesn't exist on Mac), never `python3` (system Python at `/usr/bin/python3.9` lacks our 40 pinned deps).

```bash
# CORRECT
.venv/bin/python -c "..."
.venv/bin/python scanner/foo.py

# WRONG
python ...        # command not found
python3 ...       # ModuleNotFoundError on requests, pyyaml, etc.
```

If a tool result shows `command not found: python`, the fix is `.venv/bin/python`, not `python3`. Don't keep escalating.

---

## 2. Working directory

All commands run from repo root: `~/code/tietiy-scanner` (= `/Users/abhisheklalwani/code/tietiy-scanner`).

If a Bash session drifts into `scanner/` (git operations sometimes shift cwd, or a `cd` slipped through), `cd /Users/abhisheklalwani/code/tietiy-scanner` before the next command. Don't try to chain prefixes (`cd scanner && python ...` from root works once but breaks subsequent commands assuming root-relative paths).

---

## 3. Audit-first discipline

The user runs an audit-first review pattern. Honor it:

1. **Read affected files end-to-end before editing.** Don't blind-edit. If multi-file change, propose plan first, get approval, then code.
2. **Show diff before commit.** Either `git diff <file>` or, for untracked files, show the relevant region via `Read` or `cat`. Never claim "diff applied" without visibility.
3. **Smoke-test before commit.** New behavior gets a sandboxed smoke test verified against synthetic + real data.
4. **Never auto-commit.** Wait for explicit "approved, commit" message. The user typed it for every commit tonight; assume the same next session.

If the user has explicitly said "ship it" or "auto-commit OK" in this session, follow that. Otherwise, default to audit-first.

---

## 4. Real-data safety in smoke tests

**NEVER edit real `output/*.json` or `data/*.json` files directly in smoke tests.** Production state. One bad mutation pollutes the next workflow run.

Pattern (try/finally — restores path constant + verifies real file integrity even if test raises):
```python
# Sandbox via tempfile + copy
sbx = tempfile.mkdtemp(prefix="smoke_")
shutil.copy("output/signal_history.json",
            os.path.join(sbx, "signal_history.json"))

# Monkey-patch the module's path constant — restore in finally
import rule_proposer
original_path = rule_proposer.PROPOSED_RULES_PATH
rule_proposer.PROPOSED_RULES_PATH = os.path.join(sbx, "proposed_rules.json")

try:
    # ... do test ...
finally:
    # Restore + verify real file untouched
    rule_proposer.PROPOSED_RULES_PATH = original_path
    assert sha256("output/signal_history.json") == real_hash_before
    shutil.rmtree(sbx, ignore_errors=True)
```

Standard checks at end of every smoke test: real file SHA256 unchanged, sandbox cleaned up. The try/finally matters when multiple sandboxed tests run in the same Python session — without restore, a later test inherits the previous test's patched path constant.

---

## 5. Bridge architecture quick-ref

Three composer phases, daily rhythm:

| Phase | Time IST | Composer | Behavior |
|---|---|---|---|
| L1 PRE_MARKET | 8:55 | `composers/premarket.py` | Decision brief; full bucket grouping; ALWAYS fires on trading day |
| L2 POST_OPEN | 9:40 | `composers/postopen.py` | Gap evaluation + bucket re-assignment; CONDITIONAL alert via `should_send_telegram` (only fires on bucket_change OR severe gap) |
| L4 EOD | 16:00 | `composers/eod.py` | Retrospective digest; ALWAYS fires; plain-dict EOD SDRs (no `bucket` field — the signal is closed) |

**Read-only invariant:** Bridge composers are READ-ONLY w.r.t. `signal_history.json`. `outcome_evaluator.py` (called from `eod_master.yml` at 15:35) is the sole mutator. By the time `eod.py` fires at 16:00, today's resolutions are already in signal_history.

**Single chokepoint:** Composers write only to `output/bridge_state.json` (via `state_writer.write_state` — atomic + 30-day history). Telegram renderers read state; they NEVER read truth files directly. Single source of truth.

**Renderer escape pattern:** Any literal between two `_esc()` calls is a reserved-char leak vector (`=`, `.`, `+`, `-`, `_` in MarkdownV2). When in doubt, build pieces as plain strings and `_esc` whole body once. (Caught + fixed in `_render_contra_section` 2026-04-26.)

---

## 6. Trigger words (fast context recovery)

When the user opens a session with one of these, read the listed docs before any other action:

| Trigger | Context | Read order |
|---|---|---|
| `apex` / `kabu` | Full TIE TIY context | `doc/session_context.md` → `doc/fix_table.md` → `doc/bridge_design_v1.md` |
| `morningstar` / `vedu` | GitHub scanner context | `doc/session_context.md` |
| `lucifer` | Colab backtest context | (Colab notebooks, not in repo) |
| `fixlog` | Bug fix mode | `doc/fix_table.md` first |
| `uibuild` | UI redesign mode | (Wave UI track docs — TBD) |
| `phase2` | Phase 2 build mode | `doc/roadmap.md` + `doc/session_context.md` |

---

## 7. Commit message convention

Lowercase component prefix, em-dash separator, descriptive after. Examples from `git log`:

- `bridge: composers/eod.py + bridge.py wiring — Wave 3 L4 EOD composer skeleton`
- `bridge: bridge_telegram_eod.py — EOD digest renderer (Wave 3 Session B)`
- `bridge: telegram_bot.py — /reject_rule command (Wave 4)`
- `doc: fix_table.md — Wave 3 Session A/B + Wave 4 Step 1 shipped status`

Every commit gets the `Co-Authored-By: Claude Opus 4.7 (1M context)` trailer per heredoc pattern. Push with `--rebase` fallback if remote moved (bot commits from postopen.yml etc. land on `main`).

---

**Last updated:** 2026-04-26 late-night
