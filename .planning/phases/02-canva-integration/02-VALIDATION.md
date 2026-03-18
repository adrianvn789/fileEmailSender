---
phase: 2
slug: canva-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | CANV-01 | unit (mock httpx) | `uv run pytest tests/test_canva_api.py::test_list_pages -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | CANV-02 | unit | `uv run pytest tests/test_pages.py::test_find_divider -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | CANV-03 | unit | `uv run pytest tests/test_exporter.py::test_extract_name -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | CANV-04 | unit (mock httpx) | `uv run pytest tests/test_exporter.py::test_export_pipeline -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_canva_api.py` — stubs for CANV-01: mock httpx responses for list_pages, get_design, token exchange
- [ ] `tests/test_pages.py` — stubs for CANV-02: divider detection with case-insensitive contains logic
- [ ] `tests/test_exporter.py` — stubs for CANV-03 + CANV-04: name extraction heuristic + export job polling
- [ ] `tests/conftest.py` — shared fixtures: mock httpx client, sample PDF bytes, fake token data

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Name extraction matches visible certificate text | CANV-03 | Requires real Canva design export to validate heuristic | Run `uv run python -m canva_client` with real design ID, visually compare extracted names with certificate images |
| Rate limit handling on 10+ page design | CANV-04 | Requires real API calls with realistic page count | Export a design with 10+ certificate pages, verify no 429 errors |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
