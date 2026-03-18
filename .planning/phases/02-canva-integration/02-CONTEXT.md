# Phase 2: Canva Integration - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Authenticate with Canva API, list all pages of a design, isolate certificate pages after the "Participantes" divider, extract a participant name from each certificate page via text element reading, and export each page as a PDF.

</domain>

<decisions>
## Implementation Decisions

### Name extraction strategy
- Names are in a **specific textbox element** on each certificate page — this is a Canva design with text elements, not just page titles
- Use the Canva API to read text elements from design pages to extract participant names
- The certificate is a template with a name textbox per page — each page represents one participant's certificate

### Divider detection
- The "Participantes" divider is a page with a single textbox containing the word "Participantes"
- Detection should use **contains** logic (case-insensitive substring match on text elements), not exact page title match
- All pages before and including the divider are skipped; certificate pages come after it

### Claude's Discretion
All remaining implementation details are at Claude's discretion:
- **Auth flow**: OAuth 2.0 PKCE implementation, browser redirect handling, token storage and refresh strategy
- **Which textbox holds the name**: Heuristic for identifying the name textbox among potentially multiple textboxes on a certificate page (e.g., largest text, specific position, filtering out static labels)
- **Export strategy**: Async export job creation, polling interval, concurrency, rate limit handling
- **Error handling**: API error retries, timeout handling, partial failure recovery
- **Module structure**: How to organize the Canva API client code within the existing `src/canva_client/` package
- **Design ID input**: How the user provides the Canva design ID (already in `.env` as noted in success criteria)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above.

- `.planning/REQUIREMENTS.md` — CANV-01 through CANV-04 define the Canva integration requirements
- `.planning/ROADMAP.md` — Phase 2 success criteria define exact verification targets
- `src/canva_client/config.py` — Existing config module with `CANVA_CLIENT_ID`, `CANVA_CLIENT_SECRET` env vars
- `src/canva_client/models.py` — `Certificate(page_number, name, export_url)` dataclass to populate

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config.py`: Already loads `CANVA_CLIENT_ID` and `CANVA_CLIENT_SECRET` from `.env`
- `models.py`: `Certificate` dataclass ready to populate with `page_number`, `name`, `export_url`
- `matcher.py`: `normalize_name()` can be reused for normalizing extracted names before matching

### Established Patterns
- `uv` for dependency management — new deps (httpx/requests, etc.) go in `pyproject.toml`
- `validate_config()` pattern — called explicitly, not at import time (to avoid pytest issues)
- Exit codes: 0 = success, 1 = partial failure, 2 = config error

### Integration Points
- `cli.py` will need a Canva subcommand or pipeline step that calls the new Canva module
- `Certificate` objects created here feed into Phase 3's matching pipeline
- Config validation may need a new env var for `CANVA_DESIGN_ID`

</code_context>

<specifics>
## Specific Ideas

- Names live in textbox elements on each certificate page — this is a Canva design where each page is one participant's certificate with their name in a text element
- The "Participantes" divider page has a single textbox with that word — use contains-based detection to keep it flexible

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-canva-integration*
*Context gathered: 2026-03-18*
