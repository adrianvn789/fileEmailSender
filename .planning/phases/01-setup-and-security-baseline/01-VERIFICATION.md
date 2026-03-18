---
phase: 01-setup-and-security-baseline
verified: 2026-03-18T00:36:43Z
status: passed
score: 5/5 must-haves verified
---

# Phase 1: Setup and Security Baseline — Verification Report

**Phase Goal:** The project is safe to develop — credentials can never be committed, the dependency stack is locked, core data models are defined, and the matcher is fully unit-tested against real name data before any API call is made.
**Verified:** 2026-03-18T00:36:43Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running CLI with missing `.env` variable exits code 2 with human-readable error naming the variable | VERIFIED | `test_missing_env_var_exits_2` and `test_missing_env_var_names_variable` both PASS; `config.py` prints `"Error: required environment variable '{var}' is not set."` to stderr and calls `sys.exit(2)` |
| 2 | `.gitignore` prevents `.env`, `credentials.json`, `token.json`, and `*.pdf` from being staged | VERIFIED | `git check-ignore -v` confirms all four patterns are active; `.gitignore` lines 2-7 cover all targets |
| 3 | `uv run pytest` passes with matcher tests at high-confidence, below-threshold, and no-match levels | VERIFIED | 18/18 tests pass in 0.13s; parametrized cases cover exact match (True), word-reordered (True), accent-normalized (True), below-threshold (False), no-match (False) |
| 4 | `Certificate`, `Attendee`, `MatchResult`, `PipelineResult` dataclasses instantiate without error | VERIFIED | `test_models.py` has 4 passing tests covering all four dataclasses including `PipelineResult` default-factory fields |
| 5 | `MATCH_THRESHOLD` defaults to 90 when not set in environment | VERIFIED | `config.py` line 26: `int(os.environ.get("MATCH_THRESHOLD", "90"))`; confirmed `uv run python -c "from canva_client.config import MATCH_THRESHOLD; print(MATCH_THRESHOLD)"` outputs `90` |

**Score:** 5/5 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/canva_client/config.py` | Env var loading and validation | VERIFIED | Exports `validate_config`, `MATCH_THRESHOLD`, `NAME_COLUMN`, `EMAIL_COLUMN`; 29 lines, substantive implementation |
| `src/canva_client/models.py` | Core data models | VERIFIED | Exports `Certificate`, `Attendee`, `MatchResult`, `PipelineResult` as dataclasses; 32 lines |
| `src/canva_client/matcher.py` | Fuzzy name matching | VERIFIED | Exports `normalize_name`, `match_name`, `match_all`; 62 lines; uses `partial_token_sort_ratio` with `processor=None` |
| `src/canva_client/cli.py` | CLI entry point with validate_config call | VERIFIED | Calls `validate_config()` in `main()`; `__name__ == "__main__"` guard present; 15 lines |
| `.gitignore` | Credential and artifact exclusions | VERIFIED | Contains `.env`, `credentials.json`, `token.json`, `*.pdf`; 16 lines |
| `tests/test_matcher.py` | Matcher unit tests | VERIFIED | 66 lines (min 40); covers normalize, match_name (5 parametrized cases), match_all (3 scenarios) |
| `tests/test_config.py` | Config validation tests | VERIFIED | 26 lines (min 20); subprocess tests verifying exit code 2 and stderr content |
| `tests/test_models.py` | Dataclass instantiation tests | VERIFIED | 31 lines (min 15); 4 tests covering all four dataclasses |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/canva_client/cli.py` | `src/canva_client/config.py` | `validate_config()` call in `main()` | WIRED | Line 8: `validate_config()` called directly inside `main()`; import on line 3 |
| `src/canva_client/matcher.py` | `src/canva_client/models.py` | imports `Certificate`, `Attendee`, `MatchResult`, `PipelineResult` | WIRED | Line 4: `from canva_client.models import Certificate, Attendee, MatchResult, PipelineResult` — all four used in function signatures and return values |
| `src/canva_client/matcher.py` | `src/canva_client/config.py` | imports `config.MATCH_THRESHOLD` for default threshold | WIRED | Line 5: `from canva_client import config`; `config.MATCH_THRESHOLD` used as default in both `match_name` and `match_all` signatures |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CONF-01 | 01-01-PLAN.md | API keys, SMTP credentials, and sheet ID are loaded from `.env` file | SATISFIED | `config.py` calls `load_dotenv()` at module level; `.env.example` documents all 9 vars; `_REQUIRED_VARS` list covers all credential env vars |
| CONF-02 | 01-01-PLAN.md | Tool returns meaningful exit codes (0 = success, 1 = partial failure, 2 = config error) | SATISFIED | `validate_config()` calls `sys.exit(2)` on missing var; `cli.py:main()` calls `sys.exit(0)` on success; both verified by passing subprocess tests |

Both Phase 1 requirements are marked complete in `REQUIREMENTS.md` traceability table. No orphaned requirements found — only CONF-01 and CONF-02 are mapped to Phase 1 in the traceability matrix.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | No anti-patterns found |

No TODO/FIXME/placeholder comments found in any modified files. No stub implementations. No empty handlers. No `return null`/`return {}` patterns.

---

## Human Verification Required

None. All success criteria are fully verifiable programmatically:
- Git ignore rules confirmed via `git check-ignore -v`
- All 18 tests pass with `uv run pytest`
- Exit codes verified via subprocess tests
- MATCH_THRESHOLD default confirmed via Python import

---

## Commit Verification

Commits documented in SUMMARY exist in git log:
- `a27c712` — feat(01-01): project scaffold with credential safety and config module
- `0f09016` — test(01-01): add failing tests for models, matcher, and config
- `d48b303` — feat(01-01): implement data models, fuzzy matcher, and fix CLI module invocation

All three commits present and verified.

---

## Notable Deviation from Plan

The SUMMARY records one intentional deviation from the PLAN specification: `partial_token_sort_ratio` was used instead of `token_sort_ratio`. This was required because `token_sort_ratio` scores "Maria Silva" vs "Mariana Silva" at 91.7 (above the 90 threshold), causing a false positive match. `partial_token_sort_ratio` scores this pair at 81.8, correctly rejecting it. The test suite requires this pair to return `matched=False`, so the deviation is correct and verified by the passing tests.

The PLAN's `must_haves.artifacts` entry for `matcher.py` specifies `pattern: "config\\.MATCH_THRESHOLD"` — the actual code uses `config.MATCH_THRESHOLD` as a default argument (e.g., `threshold: int = config.MATCH_THRESHOLD`), which satisfies the intent. Pattern is present in the file.

---

_Verified: 2026-03-18T00:36:43Z_
_Verifier: Claude (gsd-verifier)_
