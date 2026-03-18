# Phase 1: Setup and Security Baseline - Research

**Researched:** 2026-03-17
**Domain:** Python project scaffolding (uv), credential hygiene (.env + .gitignore), dataclasses, rapidfuzz fuzzy matching, pytest
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Project structure**: Standard Python package with `src/` layout, `uv` for dependency management
- **Match confidence tiers**: Simple two-tier — above threshold = match, below = no match. Threshold at 90 (rapidfuzz token_sort_ratio)
- **Name normalization**: Unicode normalize (NFD → strip accents), lowercase, collapse whitespace. No special handling for multi-part surnames — rapidfuzz token_sort_ratio handles word reordering naturally
- **Data model fields**: Minimal — only what's needed for the pipeline. Certificate (page_number, name, export_url), Attendee (name, email), MatchResult (certificate, attendee, score, matched: bool), PipelineResult (matches, unmatched_attendees, unmatched_certificates, errors)
- **Env vars**: `CANVA_CLIENT_ID`, `CANVA_CLIENT_SECRET`, `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_PATH`, `SMTP_USER`, `SMTP_PASSWORD`, `MATCH_THRESHOLD` (default 90), `NAME_COLUMN` (default 0), `EMAIL_COLUMN` (default 1)
- **Exit codes**: 0 = success, 1 = partial failure, 2 = config error (per CONF-02)

### Claude's Discretion
All implementation decisions for this phase are at Claude's discretion. User wants straightforward, working defaults.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONF-01 | API keys, SMTP credentials, and sheet ID are loaded from `.env` file | python-dotenv 1.2.2 `load_dotenv()` + manual required-var validation with `sys.exit(2)` |
| CONF-02 | Tool returns meaningful exit codes (0 = success, 1 = partial failure, 2 = config error) | Python `sys.exit(code)` standard; exit 2 is the POSIX convention for "misuse / bad arguments / bad config" |
</phase_requirements>

---

## Summary

Phase 1 is a greenfield Python project bootstrap: initialize a `uv` package with `src/` layout, wire up credential safety (`.env` + `.gitignore`), define four dataclasses, and implement + unit-test a pure fuzzy name matcher. No external APIs are called — everything is testable offline.

The stack is narrow and stable: `uv` manages the virtualenv and lock file, `python-dotenv` loads `.env`, `rapidfuzz` provides `token_sort_ratio`, and `pytest` runs the tests. All four libraries are mature and well-understood. The only decision requiring care is rapidfuzz's **v3 preprocessing change** — strings are no longer preprocessed by default, so the normalization step must be done explicitly before scoring.

**Primary recommendation:** Use `uv init --package`, wire `src/canva_client/` as the root package, validate env vars with a simple `_require_env()` helper that calls `sys.exit(2)` on missing vars, and keep all dataclasses as plain `@dataclass` (not frozen) to stay simple for now.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| uv | latest (install separately) | Virtualenv, dependency resolution, lock file, `uv run` | Fastest modern Python toolchain; replaces pip+venv+pip-tools in one tool |
| python-dotenv | 1.2.2 | Load `.env` into `os.environ` | Standard for CLI config; 200M+ downloads/month |
| rapidfuzz | 3.14.3 | Fuzzy string matching (`token_sort_ratio`) | C++ backed, 10-100x faster than fuzzywuzzy; MIT license |
| pytest | 9.0.2 | Test runner | Universally standard Python test framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unicodedata (stdlib) | Python 3.12 stdlib | NFD normalization + accent stripping | Already available — no install needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rapidfuzz | fuzzywuzzy | fuzzywuzzy is slower, requires python-Levenshtein separately, and is less maintained |
| uv | poetry / pip+venv | Poetry slower; uv produces a compatible pyproject.toml and is faster at resolution |
| plain dataclass | pydantic | Pydantic is heavier; no validation needed here, plain dataclass is sufficient |

**Installation (after uv is installed):**
```bash
uv init --package canva-client
cd canva-client
uv add python-dotenv rapidfuzz
uv add --dev pytest
```

**Version verification (verified 2026-03-17):**
```
rapidfuzz:      3.14.3  (latest)
python-dotenv:  1.2.2   (latest)
pytest:         9.0.2   (latest)
```

---

## Architecture Patterns

### Recommended Project Structure
```
canva-client/
├── .env                    # NOT committed — loaded by python-dotenv
├── .env.example            # Committed — documents required vars (empty values)
├── .gitignore              # Blocks .env, credentials.json, token.json, *.pdf
├── pyproject.toml          # uv project definition + pytest config
├── uv.lock                 # Committed — exact dependency snapshot
├── src/
│   └── canva_client/
│       ├── __init__.py
│       ├── config.py       # load_dotenv() + _require_env() + env accessors
│       ├── models.py       # Certificate, Attendee, MatchResult, PipelineResult
│       └── matcher.py      # normalize_name() + match_name() + match_all()
└── tests/
    ├── __init__.py
    └── test_matcher.py     # Unit tests for fuzzy matcher (offline, no API)
```

### Pattern 1: Required Env Var Validation with Exit Code 2

**What:** Call `load_dotenv()` at startup, then validate each required var with a helper. Exit with code 2 and a message naming the missing var.
**When to use:** At CLI entry point (or at `config.py` import time for fail-fast behavior).

```python
# src/canva_client/config.py
# Source: python-dotenv PyPI docs + POSIX exit code conventions
import os
import sys
from dotenv import load_dotenv

load_dotenv()  # reads .env from cwd upward; no-op if file absent

_REQUIRED_VARS = [
    "CANVA_CLIENT_ID",
    "CANVA_CLIENT_SECRET",
    "GOOGLE_SHEET_ID",
    "GOOGLE_CREDENTIALS_PATH",
    "SMTP_USER",
    "SMTP_PASSWORD",
]

def validate_config() -> None:
    """Call once at startup. Exits 2 with a human-readable message on missing var."""
    for var in _REQUIRED_VARS:
        if not os.environ.get(var):
            print(f"Error: required environment variable '{var}' is not set.", file=sys.stderr)
            sys.exit(2)

# Optional vars with defaults
MATCH_THRESHOLD: int = int(os.environ.get("MATCH_THRESHOLD", "90"))
NAME_COLUMN: int = int(os.environ.get("NAME_COLUMN", "0"))
EMAIL_COLUMN: int = int(os.environ.get("EMAIL_COLUMN", "1"))
```

**Key point:** `validate_config()` is NOT called on import — it is called explicitly from the CLI entry point so tests can import `config` without triggering exit.

### Pattern 2: Dataclasses — Plain, Not Frozen

**What:** `@dataclass` with typed fields. No `frozen=True` to avoid CPython pickling quirks with `__slots__`. Fields are only what the pipeline needs.

```python
# src/canva_client/models.py
# Source: Python 3.12 stdlib dataclasses docs
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Certificate:
    page_number: int
    name: str
    export_url: str

@dataclass
class Attendee:
    name: str
    email: str

@dataclass
class MatchResult:
    certificate: Certificate
    attendee: Attendee
    score: float
    matched: bool

@dataclass
class PipelineResult:
    matches: list[MatchResult] = field(default_factory=list)
    unmatched_attendees: list[Attendee] = field(default_factory=list)
    unmatched_certificates: list[Certificate] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
```

### Pattern 3: Fuzzy Matcher with Explicit Normalization

**What:** Normalize names to NFC/NFD-stripped ASCII-friendly form before scoring. Pass pre-normalized strings to `token_sort_ratio` with `processor=None` (since we normalize ourselves).
**When to use:** Always — rapidfuzz 3.x no longer preprocesses by default.

```python
# src/canva_client/matcher.py
# Source: rapidfuzz 3.x docs https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html
import unicodedata
from rapidfuzz import fuzz
from canva_client.models import Certificate, Attendee, MatchResult, PipelineResult
from canva_client import config

def normalize_name(name: str) -> str:
    """NFD decompose → strip combining characters → lowercase → collapse whitespace."""
    nfd = unicodedata.normalize("NFD", name)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return " ".join(stripped.lower().split())

def match_name(cert_name: str, attendee_name: str, threshold: int = config.MATCH_THRESHOLD) -> tuple[float, bool]:
    """Returns (score, matched). Score is 0-100."""
    score = fuzz.token_sort_ratio(
        normalize_name(cert_name),
        normalize_name(attendee_name),
        processor=None,  # we normalize ourselves; don't double-process
    )
    return score, score >= threshold

def match_all(
    certificates: list[Certificate],
    attendees: list[Attendee],
    threshold: int = config.MATCH_THRESHOLD,
) -> PipelineResult:
    """Greedy best-match: for each certificate, find the highest-scoring attendee."""
    result = PipelineResult()
    matched_attendees: set[int] = set()

    for cert in certificates:
        best_score = -1.0
        best_attendee = None
        best_idx = -1
        for idx, attendee in enumerate(attendees):
            if idx in matched_attendees:
                continue
            score, _ = match_name(cert.name, attendee.name, threshold)
            if score > best_score:
                best_score = score
                best_attendee = attendee
                best_idx = idx

        if best_attendee and best_score >= threshold:
            result.matches.append(
                MatchResult(cert, best_attendee, best_score, matched=True)
            )
            matched_attendees.add(best_idx)
        else:
            result.unmatched_certificates.append(cert)

    for idx, attendee in enumerate(attendees):
        if idx not in matched_attendees:
            result.unmatched_attendees.append(attendee)

    return result
```

### Pattern 4: pyproject.toml with pytest configured

```toml
# pyproject.toml
[project]
name = "canva-client"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "python-dotenv>=1.2.2",
    "rapidfuzz>=3.14.3",
]

[project.scripts]
canva-client = "canva_client.cli:main"

[build-system]
requires = ["uv_build"]
build-backend = "uv_build"

[dependency-groups]
dev = ["pytest>=9.0.2"]

[tool.pytest.ini_options]
addopts = ["--import-mode=importlib"]
testpaths = ["tests"]
```

### Anti-Patterns to Avoid
- **Calling `validate_config()` on module import:** Tests will `sys.exit(2)` unless a full `.env` is present. Keep it call-explicit.
- **Using `processor=utils.default_process` without custom normalization:** rapidfuzz's default processor lowercases and strips non-alphanumerics, which discards useful Unicode. Do normalization yourself.
- **Committing `.env`:** Always verify `.gitignore` blocks it before any `git add`.
- **`frozen=True` + `__slots__` together on Python < 3.10:** CPython bug; avoid on this Python 3.12 target (it works on 3.12, but unnecessary complexity here).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| .env loading | Custom file parser | `python-dotenv` | Handles quoting, multi-line values, comments, override logic |
| Fuzzy string matching | Levenshtein distance from scratch | `rapidfuzz.fuzz.token_sort_ratio` | Token sorting handles word order; C++ backend handles performance; edge cases (empty strings, unicode) already covered |
| Accent stripping | Custom transliteration table | `unicodedata.normalize("NFD", s)` + strip Mn category | stdlib covers all Unicode combining characters correctly |

**Key insight:** The only custom logic needed is the thin `normalize_name()` wrapper and the `_require_env()` helper — everything else delegates to libraries.

---

## Common Pitfalls

### Pitfall 1: rapidfuzz 3.x Preprocessing Change
**What goes wrong:** Code written against fuzzywuzzy or rapidfuzz 2.x assumes strings are preprocessed (lowercased, punctuation removed). In rapidfuzz 3.x, `processor=None` is the default — "Mariana Pérez" and "mariana perez" score below 100.
**Why it happens:** Breaking change in 3.0: preprocessing opt-in, not opt-out.
**How to avoid:** Always call `normalize_name()` on both strings before passing to `token_sort_ratio`. Pass `processor=None` explicitly to signal intent.
**Warning signs:** High-confidence matches scoring unexpectedly low on accented names.

### Pitfall 2: `.env` accidentally committed
**What goes wrong:** API keys appear in git history. Impossible to fully remove without rewriting history.
**Why it happens:** `.gitignore` not set up before first `git add .`.
**How to avoid:** Create `.gitignore` as the FIRST file in the project before any other `git add`. Verify with `git check-ignore -v .env`.
**Warning signs:** `git status` shows `.env` as an untracked file after the gitignore is set — if you don't see it, it's either ignored (good) or already staged (bad).

### Pitfall 3: `load_dotenv()` silently succeeds when `.env` is absent
**What goes wrong:** `load_dotenv()` returns `False` when no `.env` file is found but does not raise. Required vars remain unset. Validation must happen explicitly.
**Why it happens:** python-dotenv design: loading is best-effort. See GitHub issue #321.
**How to avoid:** Always follow `load_dotenv()` with `validate_config()` at the CLI entry point. Never assume vars are set just because load succeeded.
**Warning signs:** `os.environ.get("CANVA_CLIENT_ID")` returns `None` in production even though `.env` exists in a different directory.

### Pitfall 4: Test imports trigger `validate_config()` and exit
**What goes wrong:** If `validate_config()` is called at module level in `config.py`, `pytest` exits with code 2 unless a full `.env` is present in the test environment.
**Why it happens:** pytest imports `src/canva_client/config.py` during collection.
**How to avoid:** Keep `validate_config()` call-explicit — only invoke it from `cli.py`'s `main()` function, never at import time.

### Pitfall 5: uv not on PATH in fresh CI environment
**What goes wrong:** `uv run pytest` fails with command not found.
**Why it happens:** `uv` is not installed system-wide by default.
**How to avoid:** Document install step: `curl -LsSf https://astral.sh/uv/install.sh | sh`. Verify with `uv --version` before project setup.

---

## Code Examples

Verified patterns from official sources:

### .gitignore for this project
```gitignore
# Credentials — NEVER commit these
.env
credentials.json
token.json

# Certificate PDFs
*.pdf

# Python / uv artifacts
__pycache__/
*.py[cod]
.venv/
dist/
*.egg-info/
.pytest_cache/
```

### Running tests
```bash
uv run pytest                    # full suite
uv run pytest tests/test_matcher.py -x    # stop on first failure
uv run pytest -v                 # verbose output
```

### Verifying .gitignore works
```bash
git check-ignore -v .env         # should print: .gitignore:1:.env  .env
```

### normalize_name round-trip test pattern
```python
# tests/test_matcher.py
import pytest
from canva_client.matcher import normalize_name, match_name

def test_normalize_strips_accents():
    assert normalize_name("Mariana Pérez") == "mariana perez"

def test_normalize_handles_reordering():
    # token_sort_ratio handles word order; normalization should not affect this
    n1 = normalize_name("Silva Costa, João")
    n2 = normalize_name("João Silva Costa")
    # Both normalize to a comparable token set

@pytest.mark.parametrize("cert_name,attendee_name,expect_match", [
    ("Maria Silva",  "Maria Silva",       True),   # exact
    ("Maria Silva",  "Silva Maria",       True),   # word order
    ("Maria Pérez",  "Maria Perez",       True),   # accent difference
    ("Maria Silva",  "Mariana Silva",     False),  # below threshold
    ("Ana",          "Carlos",            False),  # no match
])
def test_match_name(cert_name, attendee_name, expect_match):
    _, matched = match_name(cert_name, attendee_name, threshold=90)
    assert matched == expect_match
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| fuzzywuzzy | rapidfuzz | 2021+ | 10-100x faster; drop-in replacement for most uses |
| rapidfuzz `processor=default_process` | `processor=None` + manual normalize | rapidfuzz 3.0 (2023) | Must normalize explicitly; avoids double-processing |
| setup.py / setup.cfg | pyproject.toml | PEP 517/518 (2019), now universal | uv uses pyproject.toml natively |
| pip + venv + pip-compile | uv | 2024 | Single tool replaces three |

**Deprecated/outdated:**
- `fuzzywuzzy`: Superseded by rapidfuzz — same API, faster, better maintained
- `setup.py` / `setup.cfg`: Use `pyproject.toml` exclusively
- `requirements.txt` as primary dependency spec: Use `pyproject.toml` `[project.dependencies]` + `uv.lock`

---

## Open Questions

1. **uv install on CI / developer machines**
   - What we know: `uv` is not available in many default CI environments
   - What's unclear: Whether the project owner has `uv` installed (it was not found on PATH during research)
   - Recommendation: Wave 0 plan task should install uv as a prerequisite step: `curl -LsSf https://astral.sh/uv/install.sh | sh`

2. **Threshold calibration**
   - What we know: 90 is the locked threshold from CONTEXT.md; token_sort_ratio is 0-100
   - What's unclear: Whether real attendee names (e.g., "José da Silva Ferreira" vs "Jose da Silva Ferreira") will consistently score ≥90 after normalization
   - Recommendation: Unit tests should include a few realistic accent-variant name pairs from the project's actual use case (Brazilian Portuguese names likely). This is a Phase 3 validation concern but the matcher unit tests should surface edge cases early.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — created in Wave 0 |
| Quick run command | `uv run pytest tests/test_matcher.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONF-01 | `.env` vars loaded into `os.environ` | unit | `uv run pytest tests/test_config.py -x` | ❌ Wave 0 |
| CONF-01 | Missing required var exits with code 2 | unit (subprocess) | `uv run pytest tests/test_config.py::test_missing_var_exits_2 -x` | ❌ Wave 0 |
| CONF-02 | Exit code 2 on config error | unit (subprocess) | `uv run pytest tests/test_config.py::test_exit_code_2 -x` | ❌ Wave 0 |
| CONF-02 | Fuzzy matcher at high-confidence threshold | unit | `uv run pytest tests/test_matcher.py::test_match_name -x` | ❌ Wave 0 |
| CONF-02 | Fuzzy matcher below threshold | unit | `uv run pytest tests/test_matcher.py::test_below_threshold -x` | ❌ Wave 0 |
| CONF-02 | Fuzzy matcher no match | unit | `uv run pytest tests/test_matcher.py::test_no_match -x` | ❌ Wave 0 |
| CONF-02 | All four dataclasses instantiate without error | unit | `uv run pytest tests/test_models.py -x` | ❌ Wave 0 |

**Note on exit code 2 testing:** Use `subprocess.run(["uv", "run", "canva-client"], capture_output=True)` and assert `returncode == 2`. Do not monkeypatch `sys.exit` — test the real exit behavior.

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_matcher.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — empty init for test discovery
- [ ] `tests/test_matcher.py` — covers fuzzy matcher (normalize + match_name + match_all)
- [ ] `tests/test_models.py` — covers instantiation of all four dataclasses
- [ ] `tests/test_config.py` — covers load_dotenv behavior + exit code 2 on missing var
- [ ] `pyproject.toml` with `[tool.pytest.ini_options]` — `--import-mode=importlib`, testpaths = ["tests"]
- [ ] Framework install: `curl -LsSf https://astral.sh/uv/install.sh | sh` — uv not found on PATH during research

---

## Sources

### Primary (HIGH confidence)
- rapidfuzz PyPI / official docs (https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html) — token_sort_ratio signature, processor parameter, v3 preprocessing change
- pytest official docs (https://docs.pytest.org/en/stable/explanation/goodpractices.html) — src layout, importlib mode, pyproject.toml config
- uv official docs (https://docs.astral.sh/uv/concepts/projects/init/) — `uv init --package`, src layout structure, pyproject.toml format
- Python 3.12 stdlib — `unicodedata` NFD normalization, `dataclasses`, `sys.exit`
- pip version registry (verified live 2026-03-17) — rapidfuzz 3.14.3, python-dotenv 1.2.2, pytest 9.0.2

### Secondary (MEDIUM confidence)
- python-dotenv PyPI (https://pypi.org/project/python-dotenv/) — load_dotenv() behavior when file absent
- python-dotenv GitHub issue #321 — `load_dotenv()` returns False (not raise) on missing file

### Tertiary (LOW confidence)
- WebSearch: uv best practices 2025 — corroborated by official uv docs; confidence elevated to MEDIUM
- WebSearch: rapidfuzz v3 preprocessing change — confirmed by official rapidfuzz docs; confidence HIGH

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified against live PyPI registry
- Architecture: HIGH — patterns derived from official docs (uv, pytest, rapidfuzz)
- Pitfalls: HIGH — rapidfuzz v3 change confirmed in official docs; dotenv silent-success confirmed in GitHub issues

**Research date:** 2026-03-17
**Valid until:** 2026-09-17 (stable libraries; re-verify if uv major version bumps)
