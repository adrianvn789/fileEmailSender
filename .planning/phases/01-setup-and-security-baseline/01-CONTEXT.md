# Phase 1: Setup and Security Baseline - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Project skeleton, credential hygiene (.env + .gitignore), core data models (Certificate, Attendee, MatchResult, PipelineResult), and pure fuzzy matcher logic with unit tests — all before any API call is made.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation decisions for this phase are at Claude's discretion. User wants straightforward, working defaults:

- **Project structure**: Standard Python package with `src/` layout, `uv` for dependency management
- **Match confidence tiers**: Simple two-tier — above threshold = match, below = no match. Threshold at 90 (rapidfuzz token_sort_ratio)
- **Name normalization**: Unicode normalize (NFD → strip accents), lowercase, collapse whitespace. No special handling for multi-part surnames — rapidfuzz token_sort_ratio handles word reordering naturally
- **Data model fields**: Minimal — only what's needed for the pipeline. Certificate (page_number, name, export_url), Attendee (name, email), MatchResult (certificate, attendee, score, matched: bool), PipelineResult (matches, unmatched_attendees, unmatched_certificates, errors)
- **Env vars**: `CANVA_CLIENT_ID`, `CANVA_CLIENT_SECRET`, `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_PATH`, `SMTP_USER`, `SMTP_PASSWORD`, `MATCH_THRESHOLD` (default 90), `NAME_COLUMN` (default 0), `EMAIL_COLUMN` (default 1)
- **Exit codes**: 0 = success, 1 = partial failure, 2 = config error (per CONF-02)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements are fully captured in REQUIREMENTS.md and the decisions above.

- `.planning/REQUIREMENTS.md` — CONF-01 and CONF-02 define the config and exit code requirements for this phase
- `.planning/ROADMAP.md` — Phase 1 success criteria define exact verification targets

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None — this phase establishes them

### Integration Points
- `.env` file will be consumed by all subsequent phases
- Data models defined here are used in Phases 2-4
- Matcher logic is used in Phase 3

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants it straightforward and working.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-setup-and-security-baseline*
*Context gathered: 2026-03-17*
