# Architecture Research

**Domain:** Python CLI tool with multiple external API integrations (Canva, Google Sheets, SMTP)
**Researched:** 2026-03-17
**Confidence:** HIGH (patterns well-established; Canva API specifics verified against OpenAPI spec)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Layer (Entry Point)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  main.py / cli.py  (Typer/Click commands)                │   │
│  │  - parse args, load config, invoke pipeline orchestrator │   │
│  └──────────────────────────┬───────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────┘
                              │ calls
┌─────────────────────────────▼───────────────────────────────────┐
│                     Orchestration Layer                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  pipeline.py  (coordinates the end-to-end flow)          │   │
│  │  - calls services in sequence                            │   │
│  │  - collects match results, flags issues, reports status  │   │
│  └──┬─────────────┬──────────────┬───────────────┬──────────┘   │
└─────┼─────────────┼──────────────┼───────────────┼─────────────┘
      │             │              │               │
      ▼             ▼              ▼               ▼
┌──────────┐ ┌──────────┐  ┌──────────────┐ ┌──────────────┐
│  Canva   │ │  Sheets  │  │   Matcher    │ │    Email     │
│ Service  │ │ Service  │  │   Service    │ │   Service    │
│          │ │          │  │              │ │              │
│ - fetch  │ │ - fetch  │  │ - fuzzy name │ │ - compose    │
│   pages  │ │   rows   │  │   matching   │ │   MIME msg   │
│ - export │ │          │  │ - flag low-  │ │ - attach PDF │
│   PDF    │ │          │  │   confidence │ │ - send SMTP  │
└────┬─────┘ └────┬─────┘  └──────────────┘ └──────────────┘
     │             │
┌────▼─────────────▼──────────────────────────────────────────────┐
│                     API Client Layer                             │
│  ┌─────────────────┐   ┌──────────────────┐                     │
│  │  canva_client   │   │  sheets_client   │                     │
│  │  (HTTP/OAuth2)  │   │  (gspread)       │                     │
│  └─────────────────┘   └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                     Infrastructure Layer                         │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │  config.py   │  │  auth.py      │  │  temp file / disk    │  │
│  │  (env vars,  │  │  (OAuth2      │  │  (PDF download       │  │
│  │   .env file) │  │   token mgmt) │  │   staging area)      │  │
│  └──────────────┘  └───────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| `cli.py` | Parse CLI args, load config, display output, handle user-facing errors | Pipeline |
| `pipeline.py` | Orchestrate end-to-end flow, collect results, report unmatched certificates | Canva Service, Sheets Service, Matcher Service, Email Service |
| `canva_service.py` | List design pages, identify the "Participantes" divider, export individual pages as PDF via async jobs | Canva API Client |
| `sheets_service.py` | Fetch attendee rows (name + email) from Google Sheet | Sheets API Client (gspread) |
| `matcher.py` | Fuzzy-match certificate page names to attendee names; return match confidence scores; flag low-confidence matches | None (pure function, no I/O) |
| `email_service.py` | Compose MIME emails with PDF attachments and send via SMTP | Python smtplib |
| `canva_client.py` | Raw HTTP communication with Canva Connect API, OAuth2 token management, export job polling | Canva REST API |
| `sheets_client.py` | Authenticate and connect to Google Sheets via gspread | Google Sheets API |
| `config.py` | Load and validate environment variables (.env file): API keys, SMTP credentials, Sheet ID | All services (injected at startup) |

## Recommended Project Structure

```
canva_cert_sender/
├── cli.py                  # Entry point, Click/Typer commands
├── pipeline.py             # Orchestrator: runs full send flow
├── config.py               # Config loading (dotenv + validation)
│
├── services/
│   ├── canva_service.py    # Business logic for Canva operations
│   ├── sheets_service.py   # Business logic for Google Sheets reads
│   ├── matcher.py          # Pure fuzzy-matching logic (no I/O)
│   └── email_service.py    # SMTP send logic
│
├── clients/
│   ├── canva_client.py     # HTTP wrapper for Canva Connect API
│   └── sheets_client.py    # gspread wrapper for Google Sheets API
│
├── models.py               # Dataclasses: Certificate, Attendee, MatchResult
│
└── tests/
    ├── test_matcher.py     # Pure unit tests — no API calls needed
    ├── test_canva_service.py
    └── test_pipeline.py
```

### Structure Rationale

- **services/ vs clients/:** Services contain business logic (which pages are certificates, what counts as a good match). Clients contain only transport logic (HTTP calls, auth headers). This boundary makes services testable with mock clients.
- **matcher.py as pure function:** No external I/O. Input: two name strings. Output: score + boolean. Easy to unit test exhaustively with edge cases (abbreviations, typos, accents).
- **models.py centralized:** `Certificate(page_index, page_title)`, `Attendee(name, email)`, `MatchResult(certificate, attendee, score, is_confident)` — defined once, passed between layers without re-parsing.
- **pipeline.py separate from cli.py:** Pipeline can be called programmatically or tested without invoking CLI machinery.

## Architectural Patterns

### Pattern 1: Pipeline / Sequential Orchestrator

**What:** A top-level function executes discrete phases in a fixed sequence. Each phase returns a typed result that feeds the next.

**When to use:** Linear workflows where step N depends on step N-1. Exactly this tool's flow: fetch pages -> fetch attendees -> match -> export PDFs -> send emails.

**Trade-offs:** Simple, easy to debug, easy to add dry-run mode or stop-at-step flags. Not suitable if steps need to run in parallel (acceptable trade-off here — Canva export jobs are the only bottleneck and can be polled in a loop).

**Example:**
```python
def run_pipeline(config: Config) -> PipelineResult:
    pages       = canva_service.get_certificate_pages(config.design_id)
    attendees   = sheets_service.get_attendees(config.sheet_id)
    matches     = matcher.match_all(pages, attendees)
    confirmed, flagged = matcher.split_by_confidence(matches)

    for match in confirmed:
        pdf_path = canva_service.export_page_as_pdf(match.certificate.page_index)
        email_service.send(match.attendee.email, pdf_path)

    return PipelineResult(sent=confirmed, flagged=flagged)
```

### Pattern 2: Async Job Polling for Canva Exports

**What:** Canva PDF export is an asynchronous job. `POST /v1/exports` returns a job ID. Poll `GET /v1/exports/{exportId}` until status is `success` or `failed`, then download the returned URL.

**When to use:** Required — Canva's API is job-based, not synchronous.

**Trade-offs:** Adds latency management complexity. Mitigate with a simple retry loop and configurable max-wait timeout. No streaming needed; files are small (single certificate pages).

**Example:**
```python
def export_page_as_pdf(design_id: str, page_index: int) -> Path:
    job_id = canva_client.create_export_job(design_id, format="pdf", pages=[page_index])
    for _ in range(MAX_POLL_ATTEMPTS):
        job = canva_client.get_export_job(job_id)
        if job.status == "success":
            return download_pdf(job.download_urls[0])
        if job.status == "failed":
            raise CanvaExportError(f"Export failed for page {page_index}")
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError("Export job timed out")
```

### Pattern 3: Fuzzy Match with Confidence Threshold

**What:** Use `rapidfuzz` (or `thefuzz`) to score name similarity. Matches above a threshold (e.g. 85) auto-confirm; below threshold are flagged for manual review. Print flagged matches to terminal before sending.

**When to use:** Any time source and destination data have format inconsistencies (the exact case here: Canva names vs. Google Sheet names).

**Trade-offs:** Threshold tuning required. Default 85 is a reasonable starting point. Flagged items require human approval or a `--force` flag to skip review.

## Data Flow

### Full Pipeline Flow

```
User runs: python cli.py send --design-id ABC --sheet-id XYZ --smtp-user ...
    │
    ▼
config.py loads .env + validates required fields
    │
    ▼
canva_service → canva_client → GET /v1/designs/{id}/pages
    │            Returns: list of pages with titles
    │            Filters: pages after "Participantes" divider = certificate pages
    ▼
sheets_service → sheets_client (gspread) → Spreadsheet.get_all_records()
    │            Returns: list of {name, email} dicts
    ▼
matcher.py
    │            Input:  [Certificate(title, page_index)], [Attendee(name, email)]
    │            Output: [MatchResult(cert, attendee, score, is_confident)]
    ▼
pipeline splits: confirmed (score >= threshold) vs flagged (score < threshold)
    │
    ├── Print flagged matches to terminal → await user confirmation (or --force)
    │
    ▼
For each confirmed match:
    canva_service → POST /v1/exports (create job)
                 → poll GET /v1/exports/{id} until success
                 → download PDF to temp file
    │
    ▼
    email_service → compose MIMEMultipart email
                 → attach PDF (MIMEBase, base64-encoded)
                 → smtplib.SMTP_SSL → send to attendee.email
    │
    ▼
pipeline.py → print summary: N sent, M flagged, K failed
```

### Key Data Structures

```
Certificate:   page_index: int, page_title: str
Attendee:      name: str, email: str
MatchResult:   certificate: Certificate, attendee: Attendee,
               score: float (0-100), is_confident: bool
PipelineResult: sent: list[MatchResult], flagged: list[MatchResult], failed: list[str]
```

## Build Order (Component Dependencies)

Build components in this order — each layer depends on what comes before:

1. **models.py** — No dependencies. Define `Certificate`, `Attendee`, `MatchResult` first. Everything downstream uses these types.

2. **config.py** — No dependencies. Load env vars, validate required keys. All services need this at instantiation.

3. **matcher.py** — Depends only on models. Pure function, zero I/O. Build and fully unit-test before touching any API.

4. **canva_client.py** — HTTP transport only. OAuth2 token fetch, `GET /v1/designs/{id}/pages`, `POST /v1/exports`, `GET /v1/exports/{id}`. No business logic.

5. **sheets_client.py** — gspread auth + `get_all_records()`. Thin wrapper only.

6. **canva_service.py** — Depends on canva_client + models. Adds: divider-page detection, page-to-certificate mapping, export job polling, PDF download to temp file.

7. **sheets_service.py** — Depends on sheets_client + models. Adds: row-to-Attendee mapping, column name resolution.

8. **email_service.py** — Depends on config (SMTP settings) + models. Build independently of Canva/Sheets.

9. **pipeline.py** — Depends on all services + matcher. Wires everything together.

10. **cli.py** — Depends on pipeline + config. Entry point, argument parsing, output formatting.

## Integration Points

### External Services

| Service | Integration Pattern | Auth Method | Key Constraint |
|---------|---------------------|-------------|----------------|
| Canva Connect API | REST over HTTPS; async export jobs | OAuth 2.0 client credentials | Export job is async: must poll until `success` |
| Google Sheets | gspread library (Sheets API v4) | Service account JSON key | 300 requests/60s per project; fetch all rows in one call |
| Gmail/SMTP | smtplib.SMTP_SSL port 465 | App password (not account password) | Gmail requires 2FA + App Password for SMTP |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| cli.py -> pipeline.py | Direct function call, passes Config | CLI does not know about services |
| pipeline.py -> services | Direct function call, passes Config | Pipeline does not know about HTTP clients |
| services -> clients | Direct method call | Services hold client as constructor argument (injected) |
| matcher.py | Pure function, no I/O | Input/output via dataclasses only |

## Anti-Patterns

### Anti-Pattern 1: Putting API Calls in CLI Commands

**What people do:** Write the HTTP request or gspread call directly inside the `@click.command` function.

**Why it's wrong:** Impossible to test without a real API. Cannot reuse logic. CLI and business logic become entangled — changing the CLI breaks logic accidentally.

**Do this instead:** CLI command calls `pipeline.run(config)`. All API logic lives in services and clients.

### Anti-Pattern 2: One Monolithic Script

**What people do:** Single `main.py` with 400 lines doing everything in sequence.

**Why it's wrong:** When Canva's export format changes, you touch the same file as email sending. Fuzzy matching is impossible to test in isolation. Adding a `--dry-run` mode requires threading a flag through every function.

**Do this instead:** Separate services with clear interfaces. `pipeline.py` is ~50 lines. Individual services are ~80 lines each and independently testable.

### Anti-Pattern 3: Downloading All PDFs Before Sending Any

**What people do:** Export all N certificate PDFs, store them all, then send all emails in a second pass.

**Why it's wrong:** For 100 attendees, you hold 100 PDFs in temp storage simultaneously. Export jobs take 5-10 seconds each; total wait before any email sends is 8-17 minutes.

**Do this instead:** Export one PDF, send the email, delete the temp file, move to the next. Streaming one-at-a-time minimizes disk usage and gets first emails out faster.

### Anti-Pattern 4: Hardcoding Match Threshold

**What people do:** `if score > 85:` buried inside a function.

**Why it's wrong:** Threshold depends on data quality. Some users' Canva names are clean; others have heavy abbreviations. A hardcoded value is invisible and un-tunable.

**Do this instead:** Make threshold a config value with a sensible default (85). Expose as `--threshold` CLI flag.

## Scaling Considerations

This is a single-user CLI tool — scaling is not a concern. The relevant dimension is number of certificates per run.

| Certificates per Run | Architecture Adjustments |
|----------------------|--------------------------|
| 1-50 | Sequential export + send. No changes needed. |
| 50-200 | Consider exporting in batches of 5 while sending previously exported PDFs. Still sequential is fine for a CLI. |
| 200+ | Unlikely use case. If needed: async export jobs with `asyncio`, concurrent polling. Not recommended for v1. |

**Actual bottleneck:** Canva export job latency (~5-10 seconds per page). At 50 certificates, that is 4-8 minutes of wall clock time. Acceptable for a CLI tool run occasionally. Log progress per certificate so the user sees it moving.

## Sources

- Canva Connect API OpenAPI spec: https://www.canva.dev/sources/connect/api/latest/api.yml
- Canva Connect API docs overview: https://www.canva.dev/docs/connect/
- gspread documentation (v6.1.4): https://docs.gspread.org/
- Python layered architecture pattern: https://comp423-25s.github.io/resources/backend-architecture/0-layered-architecture/
- Python clean architecture patterns: https://www.glukhov.org/post/2025/11/python-design-patterns-for-clean-architecture/
- Python email with PDF attachments: https://realpython.com/python-send-email/
- Python layered architecture (general): https://github.com/eefahd/python-clean-architecture

---
*Architecture research for: Python CLI tool — Canva certificate sender*
*Researched: 2026-03-17*
