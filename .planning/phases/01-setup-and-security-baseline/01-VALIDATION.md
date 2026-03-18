---
phase: 1
slug: setup-and-security-baseline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — created in Wave 0 |
| **Quick run command** | `uv run pytest tests/test_matcher.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_matcher.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | CONF-01 | unit | `uv run pytest tests/test_config.py -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | CONF-01 | unit (subprocess) | `uv run pytest tests/test_config.py::test_missing_var_exits_2 -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | CONF-02 | unit (subprocess) | `uv run pytest tests/test_config.py::test_exit_code_2 -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | CONF-02 | unit | `uv run pytest tests/test_matcher.py::test_match_name -x` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | CONF-02 | unit | `uv run pytest tests/test_matcher.py::test_below_threshold -x` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | CONF-02 | unit | `uv run pytest tests/test_matcher.py::test_no_match -x` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | CONF-02 | unit | `uv run pytest tests/test_models.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — empty init for test discovery
- [ ] `tests/test_matcher.py` — stubs for fuzzy matcher tests
- [ ] `tests/test_models.py` — stubs for dataclass instantiation tests
- [ ] `tests/test_config.py` — stubs for config load + exit code 2 tests
- [ ] `pyproject.toml` with `[tool.pytest.ini_options]` — `--import-mode=importlib`, testpaths = ["tests"]
- [ ] uv install — `curl -LsSf https://astral.sh/uv/install.sh | sh` if not on PATH

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `.gitignore` blocks sensitive files | CONF-01 | Needs git staging check | Run `git add .env` and verify it's blocked |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
