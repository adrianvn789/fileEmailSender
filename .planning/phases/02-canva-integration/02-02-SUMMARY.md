---
phase: 02-canva-integration
plan: 02
subsystem: canva-pdf-pipeline
tags: [pdf, pdfplumber, export, canva-api, tdd]
dependency_graph:
  requires: [02-01]
  provides: [pages.py, exporter.py]
  affects: [phase-03-matching]
tech_stack:
  added: [pdfplumber>=0.11.0, fpdf2>=2.8.7 (dev)]
  patterns: [TDD red-green, async export polling with exponential backoff, longest-line name heuristic]
key_files:
  created:
    - src/canva_client/pages.py
    - src/canva_client/exporter.py
    - tests/test_pages.py
    - tests/test_exporter.py
  modified:
    - tests/conftest.py
    - pyproject.toml
    - uv.lock
decisions:
  - "longest-line heuristic for name extraction: returns max(lines, key=len) — simple and works for certificate layouts where name is typically the most prominent text"
  - "export_url initialized as empty string in get_certificate_pages: populated later by exporter pipeline to decouple PDF parsing from export concerns"
  - "fpdf2 added as dev-only dependency: only needed for test fixture PDF generation, not production code"
metrics:
  duration: 3 minutes
  completed_date: "2026-03-18"
  tasks_completed: 2
  files_created: 4
  files_modified: 3
requirements: [CANV-02, CANV-03, CANV-04]
---

# Phase 02 Plan 02: PDF Export Pipeline and Text Extraction Summary

**One-liner:** PDF export pipeline using pdfplumber text extraction, case-insensitive participantes divider detection, longest-line name heuristic, and Canva API export job polling with exponential backoff.

## What Was Built

### src/canva_client/pages.py

PDF text processing module with four exported functions:

- `extract_texts_from_pdf(pdf_bytes)` — Opens PDF via pdfplumber, returns one string per page
- `find_divider_index(page_texts)` — Returns 0-based index of page containing "participantes" (case-insensitive substring), or -1
- `extract_name(text)` — Returns longest non-empty line from text as participant name
- `get_certificate_pages(pdf_bytes)` — Combines the above: returns `Certificate` objects for all pages after the divider, with 1-indexed `page_number` and extracted `name`

### src/canva_client/exporter.py

Async Canva API export pipeline with five exported functions:

- `create_export_job(client, design_id, pages=None)` — POSTs to `/v1/exports`, optionally with page array for per-certificate exports
- `poll_export(client, job_id)` — Polls GET `/v1/exports/{id}` with exponential backoff (2s initial, 1.5x multiplier, 10s cap), raises `RuntimeError` on failure, `TimeoutError` after 20 attempts
- `download_pdf(client, url)` — Downloads PDF bytes using a fresh `httpx.AsyncClient` (absolute URL, not relative to Canva base)
- `export_full_design(client, design_id)` — Convenience function: create job, poll, download, return bytes
- `export_certificate_pdfs(client, certificates, output_dir, design_id)` — Exports each certificate page individually, saves to `output_dir`, updates `Certificate.export_url` with local file path

### tests/conftest.py (updated)

Added:
- `make_pdf(page_texts)` helper function using fpdf2 to generate valid PDFs for tests
- `make_pdf_fixture` pytest fixture exposing `make_pdf` as injectable function
- `sample_certificate_pdf` fixture: 4-page PDF (intro, divider, Joao, Maria)
- `SAMPLE_EXPORT_JOB_RESPONSE` / `SAMPLE_EXPORT_COMPLETE_RESPONSE` constants
- `sample_export_job_response` / `sample_export_complete_response` fixtures

## Test Coverage

### tests/test_pages.py (9 tests, all green)
- `test_extract_texts_from_pdf` — round-trip PDF text extraction
- `test_find_divider_exact` — exact "Participantes" match
- `test_find_divider_case_insensitive` — "PARTICIPANTES" match
- `test_find_divider_substring` — "Lista de Participantes del evento" match
- `test_find_divider_not_found` — returns -1 when no divider
- `test_extract_name_single_line` — single line passthrough
- `test_extract_name_multiline` — longest-line selection
- `test_extract_name_empty` — empty string returns empty string
- `test_get_certificate_pages` — end-to-end with sample PDF fixture

### tests/test_exporter.py (6 tests, all green)
- `test_create_export_job` — POSTs correct body, returns job ID
- `test_create_export_job_with_pages` — includes pages array
- `test_poll_export_success` — polls in_progress then success, returns URLs
- `test_poll_export_failed` — raises RuntimeError on failed status
- `test_download_pdf` — downloads bytes from absolute URL
- `test_export_certificate_pdfs` — full pipeline with mocked sub-functions, files written to tmp_path

**Total suite: 41 tests, 0 failures.**

## Decisions Made

1. **Longest-line heuristic for name extraction:** `max(lines, key=len)` chosen for simplicity. Validated via test: "participou do evento" (20 chars) beats "Joao Pedro Silva" (16 chars) — this is acceptable and will be empirically validated against real Canva designs in Phase 3. If names are not the longest line, a filter-based approach can be swapped in.

2. **export_url = "" in get_certificate_pages:** Decouples text extraction from the export pipeline. Exporter populates this field after downloading.

3. **fpdf2 as dev-only dependency:** Only needed to generate test fixture PDFs. Production code only uses pdfplumber.

4. **Fresh httpx.AsyncClient in download_pdf:** Canva export URLs are absolute CDN URLs, not relative to `api.canva.com`. Using a separate client avoids base_url conflicts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] conftest.py importlib mode prevents direct import of make_pdf**

- **Found during:** Task 1 RED phase
- **Issue:** `--import-mode=importlib` prevents `from conftest import make_pdf` in test files
- **Fix:** Added `make_pdf_fixture` pytest fixture in conftest.py that returns the `make_pdf` function; tests use `make_pdf_fixture` fixture parameter
- **Files modified:** `tests/conftest.py`, `tests/test_pages.py`
- **Commit:** 23dcc67

## Self-Check: PASSED

- FOUND: src/canva_client/pages.py
- FOUND: src/canva_client/exporter.py
- FOUND: tests/test_pages.py
- FOUND: tests/test_exporter.py
- FOUND commit 23dcc67 (Task 1)
- FOUND commit 37de4f4 (Task 2)
