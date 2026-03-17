# Feature Research

**Domain:** Certificate distribution CLI tool (Canva-to-email automation)
**Researched:** 2026-03-17
**Confidence:** MEDIUM — Canva API verified via official docs; certificate distribution tool conventions drawn from training data + adjacent domain research (web search unavailable)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Dry-run / preview mode | Any bulk-send tool that can't preview first is dangerous; users need to verify matches before emails go out | LOW | Print match table + email count without sending; flag `--dry-run` |
| Match confidence display | Fuzzy matching produces uncertain results; users must see the score before approving | LOW | Display score 0-100 alongside each match using thefuzz |
| Manual review prompt for low-confidence matches | Automatic sends on weak matches cause wrong-person delivery; users expect a human gate | MEDIUM | Threshold flag (e.g. `--threshold 80`); list unmatched/low-confidence items and prompt Y/N per entry |
| Unmatched participant report | Users need to know who did NOT get a certificate so they can follow up | LOW | Print/save a list of Google Sheet rows with no match |
| Send confirmation gate | Bulk email tools should not fire without an explicit final confirmation | LOW | "Send X certificates to X recipients? [y/N]" prompt |
| Progress feedback during send | Sending N emails takes time; a silent CLI looks frozen | LOW | Progress bar via Rich `track()` or similar per-email |
| Per-email error handling and retry log | SMTP failures happen; silently dropping a failed send is unacceptable | MEDIUM | Catch per-send exceptions, log failed recipients, continue batch |
| Idempotency / skip-already-sent guard | Re-running after partial failure should not double-send | MEDIUM | Track sent state in a local JSON/CSV log file keyed by design page ID + email |
| Meaningful exit codes | Scripts that call this tool need to know if it succeeded or partially failed | LOW | Exit 0 = all sent, Exit 1 = partial failures, Exit 2 = config error |
| Config file support | API keys, SMTP credentials, sheet ID should not be typed on every run | LOW | `.env` or `config.toml`; never hard-coded in source |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Interactive match editor | Let user remap a certificate page to a different sheet row when auto-match is wrong | MEDIUM | After dry-run display, allow user to type corrected mapping before send |
| Export match report to CSV | Event organizers often need an audit trail of who received what | LOW | Write `sent_log_YYYY-MM-DD.csv` with columns: page_index, canva_name, sheet_name, email, score, status |
| Custom email template | Generic "here is your certificate" email is baseline; custom subject/body makes communication feel personal | LOW | Jinja2 template with `{{name}}` substitution; sensible default included |
| Configurable divider page detection | Today the divider is "Participantes"; a config option allows reuse without code changes | LOW | `--divider-text "Participantes"` CLI flag with env/config fallback |
| Configurable page name extraction strategy | The Canva API does not return text from pages — the name must come from a convention (see Architecture notes). Supporting multiple strategies (page title, OCR thumbnail, position-based) future-proofs the tool | HIGH | v1 can rely on Canva page "label" field if it exists; fallback to OCR via pytesseract on thumbnails; flag `--name-strategy [label|ocr]` |
| Multi-event / multi-sheet support | Organizers run recurring events; a batch mode over multiple sheet tabs or design IDs saves repetitive work | HIGH | Out of scope for v1; flag for future |
| SMTP provider abstraction | Different orgs use SendGrid, SES, or Mailgun instead of Gmail | MEDIUM | Build around smtplib interface; provider swappable via config |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-send without review | "Make it fully automatic, no prompts" | One wrong fuzzy match sends a certificate to the wrong person; no recovery path; ruins trust | Always require explicit dry-run review or at minimum a confirmation gate before send |
| Bulk Canva certificate creation | "Generate the certificates too, not just send them" | Canva API does not support writing text into existing designs or creating new pages with personalized content — this would require a different design generation workflow entirely | Keep scope to exporting and distributing pre-existing pages; document this boundary clearly |
| Web UI dashboard | "Add a UI to track sends" | Adds frontend infrastructure (server, auth, database) that is disproportionate to the single-use CLI context; hides simplicity | CSV/JSON send log is sufficient for audit; the CLI provides all visibility needed |
| Real-time send status page | "Show live progress in a browser" | Same infrastructure cost as web UI anti-feature; WebSocket complexity for a batch job that runs in minutes | Rich progress bar in terminal provides the same value at zero cost |
| Scheduling / cron integration | "Schedule sends for 9am after the event" | Adds process management complexity; cron is already available system-wide | Document how to use cron or a task scheduler with the CLI; don't embed scheduling logic |
| Automatic CC to organizer on every email | "I want a copy of every certificate email" | At 100+ attendees this floods the organizer inbox and is harder to audit than a log file | Generate a send log CSV; offer `--summary-email` flag that sends one digest at the end |

## Feature Dependencies

```
[Config / credential loading]
    └──required-by──> [Canva API connection]
    └──required-by──> [Google Sheets read]
    └──required-by──> [SMTP send]

[Canva API connection]
    └──required-by──> [Design page list]
                          └──required-by──> [Divider page detection]
                                               └──required-by──> [Certificate page isolation]
                                                                     └──required-by──> [Name extraction]
                                                                                          └──required-by──> [Fuzzy matching]
                                                                                          └──required-by──> [Dry-run display]

[Google Sheets read]
    └──required-by──> [Fuzzy matching]

[Fuzzy matching]
    └──required-by──> [Manual review prompt]
    └──required-by──> [Unmatched participant report]
    └──required-by──> [Send confirmation gate]

[Send confirmation gate]
    └──required-by──> [PDF export per page]
                          └──required-by──> [Email send]
                                               └──required-by──> [Send log / idempotency guard]
                                               └──required-by──> [Per-email error log]

[Dry-run mode] ──enhances──> [Fuzzy matching display]
[Interactive match editor] ──enhances──> [Fuzzy matching] (optional override)
[Custom email template] ──enhances──> [Email send]
[Export match report CSV] ──enhances──> [Send log]
```

### Dependency Notes

- **Name extraction requires Canva API page list:** The Canva `GET /designs/{id}/pages` endpoint returns only page index, dimensions, and thumbnail URL — no text content. Name extraction strategy (label field, page thumbnail OCR, or user-provided mapping) must be resolved before fuzzy matching is possible. This is the highest-risk dependency in the pipeline.
- **PDF export per page requires confirmed matches:** Export should happen after review, not before. Exporting all pages upfront wastes API quota if matches are wrong. Export only confirmed matches.
- **Idempotency guard requires send log:** The guard reads the log; the log is written by successful sends. Bootstrap scenario (no log file) should be handled gracefully (treat as no sends done).
- **Interactive match editor conflicts with non-interactive mode:** A `--no-interactive` flag for CI/scripted use must skip the editor and apply threshold-only logic.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] Config / credential loading from `.env` — prerequisite for all API calls
- [ ] Canva API: list design pages, detect divider by text, isolate certificate pages
- [ ] Name extraction from pages (strategy TBD based on Canva API capabilities; may require manual page-name convention or OCR)
- [ ] Google Sheets read via gspread (name + email columns, configurable column indices)
- [ ] Fuzzy matching with configurable confidence threshold
- [ ] Dry-run display: table of page → matched name → email → confidence score
- [ ] Manual review prompt for low-confidence matches (below threshold)
- [ ] Unmatched participant list printed to terminal
- [ ] Send confirmation gate before any email is sent
- [ ] PDF export per confirmed-match page via Canva export API
- [ ] Email send via SMTP/Gmail with PDF attachment
- [ ] Progress bar during send
- [ ] Per-send error handling; failed recipients printed at end
- [ ] Send log written to local JSON file (idempotency guard on re-run)
- [ ] Meaningful exit codes

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Custom email subject/body template (Jinja2) — trigger: user asks for branded emails
- [ ] Export match report to CSV — trigger: user needs audit trail for stakeholders
- [ ] Interactive match editor — trigger: user reports frequent corrections needed
- [ ] Configurable divider page detection flag — trigger: user reuses tool for second event with different divider text
- [ ] `--summary-email` digest at end of send — trigger: user wants confirmation without CC flood

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Multi-event / multi-sheet batch mode — defer: single-event use is sufficient to validate; adds significant config complexity
- [ ] SMTP provider abstraction (SendGrid, SES) — defer: Gmail covers the current use case; abstract only when a different provider is needed
- [ ] OCR-based name extraction as default — defer: high system dependency (Tesseract install); only add if the page-label approach is unavailable

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Dry-run / preview mode | HIGH | LOW | P1 |
| Fuzzy matching with threshold | HIGH | LOW | P1 |
| Manual review prompt | HIGH | LOW | P1 |
| Unmatched participant report | HIGH | LOW | P1 |
| Send confirmation gate | HIGH | LOW | P1 |
| Per-send error handling + log | HIGH | LOW | P1 |
| Idempotency / skip-sent guard | HIGH | MEDIUM | P1 |
| Config file / `.env` support | HIGH | LOW | P1 |
| Progress bar | MEDIUM | LOW | P1 |
| Meaningful exit codes | MEDIUM | LOW | P1 |
| Custom email template | MEDIUM | LOW | P2 |
| CSV send log export | MEDIUM | LOW | P2 |
| Interactive match editor | MEDIUM | MEDIUM | P2 |
| Configurable divider flag | MEDIUM | LOW | P2 |
| Summary email digest | LOW | LOW | P2 |
| Multi-event batch mode | LOW | HIGH | P3 |
| SMTP provider abstraction | LOW | MEDIUM | P3 |
| Web UI | LOW | HIGH | P3 (anti-feature) |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

This is a custom internal automation tool, not a commercial product. The closest analogues are:

| Feature | Certify (SaaS) | Accredible (SaaS) | This Tool |
|---------|----------------|-------------------|-----------|
| Certificate source | Platform-generated | Platform-generated | Canva (user-designed) |
| Distribution trigger | Manual / automated rules | Manual / automated rules | CLI run |
| Attendee data source | Built-in CRM | Built-in CRM / CSV | Google Sheets |
| Name matching | Exact (user managed) | Exact (user managed) | Fuzzy (handles typos) |
| Dry-run / preview | Yes (UI preview) | Yes (UI preview) | Yes (terminal table) |
| Audit log | Yes (dashboard) | Yes (dashboard) | Yes (local CSV/JSON) |
| Template customization | Yes | Yes | Yes (Jinja2, v1.x) |
| Cost | SaaS subscription | SaaS subscription | Free / self-hosted |
| Canva integration | No | No | Native |

**Key differentiator of this tool:** Fuzzy name matching solves the real-world problem that Canva design page names rarely exactly match attendee list names. Commercial tools assume exact data; this tool handles the messy reality of event data.

## Critical Research Flag: Name Extraction

The Canva `GET /designs/{id}/pages` endpoint confirmed (HIGH confidence, official docs) returns **only page index, dimensions, and thumbnail URL — no text content.**

This means the pipeline assumption "extract each certificate page's participant name from the design" cannot be fulfilled via a direct API call. Three approaches:

1. **Canva page label/title convention:** If users name each Canva page after the participant (e.g., "Page title: Ana Martínez"), there may be a field in the API response not yet surfaced in docs. Needs empirical testing with a real design and API token. **Flag for Phase 1 research.**
2. **OCR on thumbnail images:** Download the thumbnail URL, run pytesseract on it, extract the largest text block as the name. Works if the name is prominent. System dependency on Tesseract install. Accuracy varies with font/layout.
3. **User-provided mapping file:** User supplies a CSV mapping page number → name. Sidesteps the extraction problem entirely at the cost of a manual step.

The recommended v1 approach is to test option 1 first (empirical API exploration), fall back to option 3 (user CSV) for launch reliability, and defer option 2 (OCR) to v1.x.

## Sources

- Canva Connect API — Export Jobs: https://www.canva.dev/docs/connect/api-reference/exports/create-design-export-job/ (HIGH confidence, official docs)
- Canva Connect API — Get Design: https://www.canva.dev/docs/connect/api-reference/designs/get-design/ (HIGH confidence, official docs)
- Canva Connect API — Get Design Pages: https://www.canva.dev/docs/connect/api-reference/designs/get-design-pages/ (HIGH confidence, official docs)
- thefuzz on PyPI: https://pypi.org/project/thefuzz/ (HIGH confidence)
- gspread on PyPI: https://pypi.org/project/gspread/ (HIGH confidence)
- Click on PyPI: https://pypi.org/project/click/ (HIGH confidence)
- Rich on PyPI: https://pypi.org/project/rich/ (HIGH confidence)
- Certify / Accredible competitor analysis: MEDIUM confidence (training data, not verified via current docs)

---
*Feature research for: Canva certificate sender CLI (Python)*
*Researched: 2026-03-17*
