---
phase: 01-setup-and-security-baseline
plan: 01
subsystem: infra
tags: [uv, python-dotenv, rapidfuzz, pytest, fuzzy-matching, dataclasses]

# Dependency graph
requires: []
provides:
  - uv Python package with src/ layout (canva-client)
  - .gitignore blocking .env, credentials.json, token.json, *.pdf
  - .env.example documenting all 9 required env vars
  - config.py: load_dotenv + validate_config() exiting code 2 on missing vars
  - models.py: Certificate, Attendee, MatchResult, PipelineResult dataclasses
  - matcher.py: normalize_name, match_name, match_all with partial_token_sort_ratio
  - 18 passing tests (models, matcher, config exit codes)
affects: [02-canva-api-integration, 03-sheet-matching-pipeline, 04-email-delivery]

# Tech tracking
tech-stack:
  added: [uv 0.10.11, python-dotenv 1.2.2, rapidfuzz 3.14.3, pytest 9.0.2]
  patterns:
    - src/ layout Python package with uv
    - validate_config() called only from CLI entry point (not on import)
    - NFD accent stripping via unicodedata before fuzzy scoring
    - partial_token_sort_ratio with processor=None for word-reorder-tolerant matching

key-files:
  created:
    - .gitignore
    - .env.example
    - pyproject.toml
    - uv.lock
    - src/canva_client/__init__.py
    - src/canva_client/config.py
    - src/canva_client/models.py
    - src/canva_client/matcher.py
    - src/canva_client/cli.py
    - src/canva_client/__main__.py
    - tests/__init__.py
    - tests/test_models.py
    - tests/test_matcher.py
    - tests/test_config.py
  modified: []

key-decisions:
  - "Used partial_token_sort_ratio instead of token_sort_ratio: token_sort_ratio scores Maria Silva vs Mariana Silva at 91.7 (above 90 threshold) making them match incorrectly; partial_token_sort_ratio scores 81.8 correctly rejecting the pair"
  - "validate_config() NOT called at import time: prevents pytest from exiting code 2 during collection when no .env is present"
  - "if __name__ == __main__ guard added to cli.py: enables python -m canva_client.cli subprocess invocation in test_config.py"
  - "uv installed via curl install script (not on PATH by default on this machine)"

patterns-established:
  - "Fuzzy matching: normalize both strings with normalize_name() then score with partial_token_sort_ratio(processor=None)"
  - "Config safety: load_dotenv() at module level, validate_config() only at CLI entry point"
  - "Test subprocess: use sys.executable with env={PATH:''} to test exit codes without inheriting env vars"

requirements-completed: [CONF-01, CONF-02]

# Metrics
duration: 18min
completed: 2026-03-17
---

# Phase 1 Plan 01: Project Bootstrap Summary

**uv canva-client package with credential-safe .gitignore, python-dotenv config validation (exit 2 on missing vars), four pipeline dataclasses, and partial_token_sort_ratio fuzzy matcher with 18 passing pytest tests**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-03-17T20:24:00Z
- **Completed:** 2026-03-17T20:42:00Z
- **Tasks:** 2 (1 scaffold + 1 TDD models/matcher)
- **Files modified:** 14 created, 1 modified (cli.py)

## Accomplishments
- uv project initialized with src/ layout; all deps installed (python-dotenv 1.2.2, rapidfuzz 3.14.3, pytest 9.0.2)
- .gitignore blocks all credentials and certificate PDFs; verified with `git check-ignore`
- config.py with validate_config() exits code 2 naming each missing env var
- Four pipeline dataclasses (Certificate, Attendee, MatchResult, PipelineResult) with 15 passing tests
- Fuzzy matcher correctly handles exact, word-reordered, accent-normalized, below-threshold, and no-match cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold with credential safety and config module** - `a27c712` (feat)
2. **Task 2 RED: Failing tests for models, matcher, config** - `0f09016` (test)
3. **Task 2 GREEN: Data models, fuzzy matcher, CLI fix** - `d48b303` (feat)

_Note: TDD task produced two commits (RED → GREEN)_

## Files Created/Modified
- `.gitignore` - Blocks .env, credentials.json, token.json, *.pdf
- `.env.example` - Documents all 9 required env vars with defaults
- `pyproject.toml` - Package def, deps, pytest config with importlib mode
- `uv.lock` - Locked dependency snapshot
- `src/canva_client/__init__.py` - Package init
- `src/canva_client/config.py` - load_dotenv + validate_config() + MATCH_THRESHOLD/NAME_COLUMN/EMAIL_COLUMN defaults
- `src/canva_client/models.py` - Certificate, Attendee, MatchResult, PipelineResult dataclasses
- `src/canva_client/matcher.py` - normalize_name, match_name, match_all using partial_token_sort_ratio
- `src/canva_client/cli.py` - Entry point wiring validate_config; __main__ guard added
- `src/canva_client/__main__.py` - Enables python -m canva_client.cli subprocess invocation
- `tests/__init__.py` - Empty test package init
- `tests/test_models.py` - 4 dataclass instantiation tests
- `tests/test_matcher.py` - 14 matcher tests (normalize, match_name parametrized, match_all scenarios)
- `tests/test_config.py` - 2 subprocess exit code tests

## Decisions Made
- `partial_token_sort_ratio` over `token_sort_ratio`: plain token_sort_ratio scores "Maria Silva" vs "Mariana Silva" at 91.7 (above 90 threshold), incorrectly matching them. partial_token_sort_ratio scores 81.8, correctly rejecting the pair while still scoring exact, reordered, and accent-normalized matches at 100.
- `validate_config()` is call-explicit (not triggered at import): prevents pytest collection from triggering sys.exit(2) when no .env file is present.
- Added `if __name__ == "__main__": main()` to cli.py: required for `python -m canva_client.cli` subprocess invocation to trigger the main() function.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Switched from token_sort_ratio to partial_token_sort_ratio**
- **Found during:** Task 2 GREEN (test execution)
- **Issue:** `fuzz.token_sort_ratio("maria silva", "mariana silva", processor=None)` = 91.7, above threshold 90. Test spec requires this pair to return `matched=False` at threshold 90.
- **Fix:** Changed scorer to `fuzz.partial_token_sort_ratio` which scores this pair at 81.8 (correctly rejects) while maintaining 100.0 for exact, word-reordered, and accent-normalized matches.
- **Files modified:** `src/canva_client/matcher.py`
- **Verification:** `uv run pytest tests/test_matcher.py -v` — all 14 matcher tests pass
- **Committed in:** d48b303

**2. [Rule 1 - Bug] Added `__name__ == "__main__"` guard to cli.py and created `__main__.py`**
- **Found during:** Task 2 GREEN (test_config.py subprocess tests)
- **Issue:** `python -m canva_client.cli` runs cli.py as a module but does not call `main()` since there was no module-level invocation. Subprocess returned exit code 0 with empty stderr.
- **Fix:** Added `if __name__ == "__main__": main()` to cli.py. Created `__main__.py` at package root for `python -m canva_client` support.
- **Files modified:** `src/canva_client/cli.py`, `src/canva_client/__main__.py` (created)
- **Verification:** `uv run pytest tests/test_config.py -v` — both subprocess tests pass
- **Committed in:** d48b303

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes required for correct test behavior and scorer accuracy. No scope creep.

## Issues Encountered
- `uv` not on PATH — installed via `curl -LsSf https://astral.sh/uv/install.sh | sh` as documented in research.
- `uv init --package` created project in a `canva-client/` subdirectory; moved contents to repo root.

## User Setup Required
None - no external service configuration required for this plan. API credentials are needed in Phase 2.

## Next Phase Readiness
- Package scaffolded and all tests passing — ready for Phase 2 Canva OAuth integration
- MATCH_THRESHOLD default (90) with partial_token_sort_ratio should be validated against real attendee name data in Phase 3
- Concern: uv not in PATH by default; Phase 2 plans should verify uv is available

---
*Phase: 01-setup-and-security-baseline*
*Completed: 2026-03-17*

## Self-Check: PASSED

- All 14 source/test files exist on disk
- All 3 task commits found in git log (a27c712, 0f09016, d48b303)
- `uv run pytest` exits 0 with 18 tests passing
