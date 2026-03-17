# Project Research Summary

**Project:** Canva Certificate Sender CLI
**Domain:** Python CLI tool — Canva API + Google Sheets + Gmail/SMTP certificate distribution
**Researched:** 2026-03-17
**Confidence:** MEDIUM (critical Canva API gap verified; name extraction strategy unresolved)

## Executive Summary

This project is a sequential automation pipeline: read a Canva design, extract individual certificate pages, match those pages to attendees in Google Sheets using fuzzy name matching, export each matched page as a PDF, and send it by email. Experts build this class of tool as a layered CLI — a thin Click entry point, a pipeline orchestrator, separate service modules per integration, and pure-function matching logic that can be unit-tested without any API calls. The recommended stack is Python 3.11+, Click, requests, gspread, rapidfuzz, pypdf, python-dotenv, rich, and smtplib from stdlib. Package management should use uv.

The single highest-risk architectural question is how to extract participant names from Canva certificate pages. The Canva Connect API confirmed (official docs, HIGH confidence) that the `GET /designs/{id}/pages` endpoint returns only page index, dimensions, and thumbnail URL — no text content. The recommended v1 strategy is: attempt PDF text extraction with pypdf on single-page exports; fall back to a user-provided CSV mapping if PDF extraction fails. This assumption must be validated in Phase 1 before building the matching pipeline, because all downstream logic depends on it.

The tool requires explicit safety gates throughout: dry-run mode must be the default, manual review must be required for matches below the confidence threshold (set at 90-95%, not the tempting 70-80%), and an explicit `--send` flag must be required before any email is dispatched. A send log keyed by page ID + email provides idempotency on re-runs. These are not nice-to-haves — they are the features that prevent sending the wrong certificate to the wrong person, which is a trust-destroying failure with no easy recovery.

## Key Findings

### Recommended Stack

The full pipeline has no dependency on a Python SDK for Canva — no official one exists. The recommended approach is raw `requests` calls against the Canva Connect REST API, with OAuth 2.0 PKCE handled manually using stdlib `hashlib` and `base64`. The first run requires a browser authorization step; subsequent runs reuse a refresh token stored in the OS keychain via `keyring`. Google Sheets access uses `gspread` with a service account (headless, no browser required). Fuzzy matching uses `rapidfuzz` — not `fuzzywuzzy` (GPL-licensed, unmaintained, known bugs). PDF text extraction uses `pypdf`; `pdfminer.six` is the explicit fallback if pypdf fails on Canva-generated PDFs. Avoid PyMuPDF (AGPL) and any OCR-first approaches in v1 (Tesseract adds a hard system dependency).

**Core technologies:**
- Python 3.11+: runtime — stable, required by Click 8.3.x and type hint ergonomics
- Click 8.3.1: CLI framework — decorator-based, simpler than Typer for a single-command pipeline
- requests 2.32.5: HTTP client for Canva API — no official Python SDK exists
- gspread 6.2.1: Google Sheets reader — service account auth works headlessly
- rapidfuzz 3.14.3: fuzzy name matching — MIT-licensed successor to fuzzywuzzy, C++ backend
- pypdf 6.9.1: PDF text extraction from Canva page exports — required due to no API text content
- python-dotenv 1.2.2: credential management — keeps secrets out of source code
- rich 14.3.3: CLI output formatting — match review table and progress output
- keyring 25.6.1: secure token storage — OS keychain for OAuth refresh tokens
- uv: package manager and venv — replaces pip + venv

### Expected Features

**Must have (table stakes):**
- Dry-run / preview mode — users cannot safely validate matches without it; default behavior
- Fuzzy matching with configurable confidence threshold — real-world event data never matches exactly
- Manual review prompt for below-threshold matches — human gate before any email is sent
- Unmatched participant report — attendees who won't receive a certificate must be visible
- Send confirmation gate — explicit Y/N before bulk send begins
- Per-email error handling and failed-send log — SMTP failures must not silently discard certificates
- Idempotency / skip-already-sent guard — re-runs after partial failure must not double-send
- Config file / `.env` support — API keys and sheet ID must not be typed on every run
- Progress bar during send — export jobs take 5-10 seconds each; the CLI must not appear frozen
- Meaningful exit codes — Exit 0 = all sent, Exit 1 = partial failures, Exit 2 = config error

**Should have (competitive):**
- Custom email subject/body template (Jinja2 with `{{name}}`) — branded communication
- CSV send log export — audit trail for event organizers
- Interactive match editor — user can remap a certificate page when auto-match is wrong
- Configurable divider page detection flag (`--divider-text`) — reuse for different events
- Summary email digest at end of run — one confirmation email instead of CC on every send

**Defer (v2+):**
- Multi-event / multi-sheet batch mode — adds significant config complexity before value is proven
- SMTP provider abstraction (SendGrid, SES) — Gmail covers the current use case
- OCR-based name extraction as default — hard system dependency (Tesseract install)

### Architecture Approach

The tool follows a strict four-layer architecture: CLI layer (Click commands, output formatting) → Orchestration layer (pipeline.py coordinates the full flow) → Service layer (canva_service, sheets_service, matcher, email_service — business logic, no HTTP) → Client/infrastructure layer (canva_client with OAuth, sheets_client via gspread, config.py, auth.py). The matcher is a pure function with no I/O, making it the only component that can be fully unit-tested without mocks. The pipeline exports and sends one certificate at a time (streaming) — not batch-download-then-send — to minimize disk usage and avoid compounding Canva export rate limits.

**Major components:**
1. `cli.py` — parse args, load config, display output, route to pipeline
2. `pipeline.py` — orchestrate end-to-end flow, collect results, report unmatched
3. `canva_service.py` — list pages, detect divider, export individual pages as async PDF jobs
4. `sheets_service.py` — fetch attendee rows (name + email) via gspread
5. `matcher.py` — pure fuzzy-matching with threshold split (auto-confirm vs. flagged)
6. `email_service.py` — compose MIME emails with PDF attachments, send via smtplib
7. `models.py` — `Certificate`, `Attendee`, `MatchResult`, `PipelineResult` dataclasses
8. `canva_client.py` — raw HTTP to Canva Connect API, OAuth PKCE, export job polling
9. `config.py` — load and validate all environment variables at startup

**Recommended build order:** models.py → config.py → matcher.py → canva_client.py → sheets_client.py → canva_service.py → sheets_service.py → email_service.py → pipeline.py → cli.py

### Critical Pitfalls

1. **Canva API has no text content endpoint** — page titles may work if the designer named each Canva page after the participant; otherwise the only fallback is user-provided CSV mapping (v1) or OCR on thumbnail images (v1.x). Spike this in Phase 1 before writing any matching logic.

2. **Canva export is asynchronous** — `POST /v1/exports` returns a job ID, not a download URL. Must poll `GET /v1/exports/{id}` until status is `"success"`. Build exponential backoff polling into the export helper from the start; retrofitting it is error-prone.

3. **Canva export rate limits will throttle large runs** — 20 export creations per minute, 75 per 5-minute window. Add a 3-4 second minimum delay between export creation calls and handle `429` responses with wait-then-retry.

4. **Fuzzy matching false positives send the wrong certificate to the wrong person** — this is the worst failure mode. Use `token_sort_ratio` from RapidFuzz (not plain `ratio`), set auto-confirm threshold at 90-95%, and require manual review for all matches below threshold. Never send without human confirmation of flagged matches.

5. **Credentials committed to version control** — set up `.gitignore` (excluding `.env`, `credentials.json`, `token.json`, `*.pdf`) before writing any code. Store all secrets in `.env`. Provide `.env.example` with placeholders.

6. **Gmail SMTP requires App Password, not account password** — `SMTPAuthenticationError` is the symptom; 2FA must be enabled first. Document as a setup prerequisite in Phase 3.

7. **Google Sheets service account not shared with the sheet** — service accounts have no access unless the spreadsheet is explicitly shared with the `client_email` from the credentials JSON. Include this as an explicit setup step.

## Implications for Roadmap

Based on research, the build order is driven by the critical unknowns (Canva API name extraction) and the dependency chain (matching requires names, sending requires confirmed matches, export happens last). Suggested phase structure:

### Phase 0: Project Setup and Security Baseline
**Rationale:** Credentials committed to version control cannot be recovered cheaply. `.gitignore`, `.env` pattern, and project scaffolding must exist before any integration code is written. This phase has zero dependencies.
**Delivers:** Repo structure, dependency management via uv, `config.py`, `.env.example`, `.gitignore`, models.py dataclasses, and a working `matcher.py` with full unit tests.
**Addresses:** Config/credential loading (table stakes), meaningful exit codes skeleton.
**Avoids:** Credentials committed to VCS (Pitfall 7). Sets up matcher as pure function before any API work.
**Research flag:** None — standard Python project setup patterns.

### Phase 1: Canva API Integration and Name Extraction Spike
**Rationale:** Name extraction is the single highest-risk assumption. All matching logic depends on it. This phase spikes the assumption empirically before building the full pipeline — if page titles don't contain participant names, the architecture must pivot before significant code exists.
**Delivers:** `canva_client.py` with OAuth PKCE, `canva_service.py` with divider detection, per-page PDF export (async polling), and a validated name extraction strategy (page title vs. user-supplied CSV).
**Addresses:** Design page listing, certificate page isolation, PDF export per page.
**Avoids:** Async export not handled (Pitfall 2), export rate limits (Pitfall 3), name extraction assumption failure (Pitfall 1).
**Research flag:** Needs empirical validation — run a real Canva API call with a real design before Phase 2 begins. The name extraction strategy cannot be finalized from docs alone.

### Phase 2: Google Sheets Integration and Matching Pipeline
**Rationale:** Once name extraction is validated, build the data input side (Sheets) and wire the matching logic. The matcher is already unit-tested from Phase 0; this phase integrates it with real data from both sources.
**Delivers:** `sheets_client.py`, `sheets_service.py`, fuzzy matching with threshold split, dry-run display (Rich table of page → matched name → email → confidence score), unmatched participant report.
**Addresses:** Google Sheets read, fuzzy matching with threshold, dry-run preview, unmatched report, manual review prompt.
**Avoids:** Fuzzy match false positives (Pitfall 4 — validate threshold against real attendee name data here), service account sharing omission (Pitfall 6).
**Research flag:** None for Sheets integration (well-documented). Fuzzy threshold tuning needs real event data — plan a validation step with actual past-event names.

### Phase 3: Email Send Pipeline and Safety Gates
**Rationale:** Email sending is irreversible. Build it last, after matching is reliable. The safety gates (confirmation prompt, dry-run default, `--send` opt-in, idempotency guard) must be part of the initial implementation — not added afterward.
**Delivers:** `email_service.py` (SMTP with PDF attachment), `pipeline.py` orchestrator, send confirmation gate, progress bar, per-send error handling, send log (idempotency), meaningful exit codes, `cli.py` entry point with all flags.
**Addresses:** Send confirmation gate, per-email error handling, idempotency guard, progress bar, exit codes, all P1 table-stakes features.
**Avoids:** Gmail SMTP auth failure (Pitfall 5 — document App Password setup as prerequisite), no dry-run mode (UX pitfall — default to dry-run, require `--send` flag).
**Research flag:** None — smtplib patterns are well-documented. Gmail App Password setup must be tested manually before phase is considered done.

### Phase 4: Polish, v1.x Features, and Hardening
**Rationale:** Once the core pipeline is proven with a real event, add the differentiator features that make the tool reusable and trustworthy.
**Delivers:** Custom email template (Jinja2), CSV send log export, configurable `--divider-text` flag, interactive match editor, `.env.example` and README with setup guide.
**Addresses:** Should-have (P2) features from FEATURES.md.
**Avoids:** None new — hardening phase.
**Research flag:** None — all are low-complexity additions to existing services.

### Phase Ordering Rationale

- Phase 0 before everything: security and project skeleton have no dependencies and prevent the costliest mistakes.
- Phase 1 before Phase 2: name extraction is the critical assumption the entire pipeline rests on. Validating it first prevents building matching logic against a broken foundation.
- Phase 2 before Phase 3: email sending requires confirmed matches; matching requires names; both data inputs must work before orchestration.
- Phase 3 as integration: pipeline orchestrator (pipeline.py) is built last because it wires together components that must already exist and be tested individually.
- Phase 4 deferred: v1.x features have value but zero impact on correctness of the core flow.

### Research Flags

Phases needing deeper investigation during planning:
- **Phase 1:** Name extraction strategy must be validated empirically. Run the `GET /v1/designs/{id}/pages` endpoint against the actual Canva design before committing to a strategy. If page titles are generic ("Page 1"), the user-CSV fallback must be the v1 approach, and the roadmap for OCR must be moved into scope.
- **Phase 2:** Fuzzy matching threshold should be validated with real attendee name data from past events before setting a production default. The 90-95% recommendation is based on research; real data may require adjustment.

Phases with standard patterns (can skip research-phase):
- **Phase 0:** Python project setup, uv, dotenv, dataclasses — all well-documented patterns.
- **Phase 3:** smtplib SMTP with PDF attachments — well-documented. Gmail App Password setup is a human prerequisite, not a code uncertainty.
- **Phase 4:** Jinja2 templates, CSV writing, Click flags — all standard Python patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library versions verified on PyPI; Canva API OAuth confirmed via official docs; no official Canva Python SDK (confirmed HIGH) |
| Features | MEDIUM | Table-stakes and differentiators drawn from domain analysis; Canva API verified HIGH; competitor comparison MEDIUM (training data) |
| Architecture | HIGH | Layered CLI patterns well-established; Canva async export pattern verified against OpenAPI spec; component boundaries are standard Python service architecture |
| Pitfalls | HIGH | Canva API limitations confirmed via official docs; Gmail SMTP issues confirmed; gspread v6 breaking changes documented; fuzzy matching failure modes verified |

**Overall confidence:** MEDIUM-HIGH — the architecture and stack are solid, but the name extraction path has one empirically unverifiable assumption until the tool is run against a real Canva design with a real API token.

### Gaps to Address

- **Canva page title convention:** The critical question — "do the certificate pages in the actual design have participant names as page titles?" — cannot be answered from documentation alone. Must be validated in Phase 1 with the real design ID and a valid API token. If page titles are generic, v1 must ship with a user-provided CSV mapping instead of automatic extraction.

- **Canva OAuth PKCE for CLI:** The browser-based PKCE flow works well for web apps but requires a local callback redirect for CLIs. The recommended pattern (print auth URL, user pastes callback URL back into terminal) is functional but has UX friction. Validate this flow works with the Canva Developer Portal app configuration before Phase 1 is done.

- **Canva `design:content:read` scope:** The required OAuth scopes for reading pages and creating export jobs must be confirmed in the Canva Developer Portal app setup. Missing scopes produce `403` errors that look like auth failures.

- **Gmail sending limits:** Gmail SMTP has a 100-email-per-day limit for personal accounts. If the target event has more than 100 attendees, this becomes a blocker. Document the limit and recommend Google Workspace for large events.

## Sources

### Primary (HIGH confidence)
- Canva Connect API — Authentication: https://www.canva.dev/docs/connect/authentication/
- Canva Connect API — Export endpoint: https://www.canva.dev/docs/connect/api-reference/exports/create-design-export-job/
- Canva Connect API — Get design pages: https://www.canva.dev/docs/connect/api-reference/designs/get-design-pages/
- Canva Connect API — Rate limits: https://www.canva.dev/docs/connect/api-requests-responses/
- gspread documentation — Authentication: https://docs.gspread.org/en/latest/oauth2.html
- gspread — HISTORY.rst (v6 breaking changes): https://github.com/burnash/gspread/blob/master/HISTORY.rst
- PyPI: rapidfuzz 3.14.3 — https://pypi.org/project/rapidfuzz/ (license, API verified)
- PyPI: Click 8.3.1 — https://pypi.org/project/click/
- PyPI: pypdf 6.9.1 — https://pypi.org/project/pypdf/
- PyPI: gspread 6.2.1 — https://pypi.org/project/gspread/

### Secondary (MEDIUM confidence)
- gspread docs — Service account auth: https://docs.gspread.org/en/latest/ (pattern verified, version MEDIUM)
- Gmail SMTP App Password requirement: https://www.pythontutorials.net/blog/cant-send-email-via-python-using-gmail-smtplib-smtpexception-smtp-auth-extension-not-supported-by-server/
- Python layered architecture pattern: https://comp423-25s.github.io/resources/backend-architecture/0-layered-architecture/
- RapidFuzz false positives in fuzzy name matching: https://github.com/rapidfuzz/RapidFuzz
- Certify / Accredible competitor analysis: training data, not verified against current docs

### Tertiary (LOW confidence — needs validation)
- OCR thumbnail fallback (pytesseract): accuracy on Canva designs with custom fonts not empirically tested
- Canva page title convention containing participant names: assumed based on user workflow description; must be verified against real design

---
*Research completed: 2026-03-17*
*Ready for roadmap: yes*
