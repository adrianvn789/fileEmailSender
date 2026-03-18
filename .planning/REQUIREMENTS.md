# Requirements: Canva Certificate Sender

**Defined:** 2026-03-17
**Core Value:** Automate the tedious process of extracting, matching, and emailing personalized event attendance certificates from Canva to attendees.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Canva Integration

- [ ] **CANV-01**: User can connect to Canva API and list pages of a design by ID
- [ ] **CANV-02**: Tool detects the "Participantes" divider page and isolates certificate pages after it
- [ ] **CANV-03**: Tool extracts the participant name from each certificate page
- [ ] **CANV-04**: Tool exports each matched certificate page as a PDF via Canva export API

### Google Sheets

- [ ] **GSHT-01**: Tool reads attendee list (name + email) from a Google Sheet
- [ ] **GSHT-02**: User can configure which columns contain name and email

### Matching

- [ ] **MTCH-01**: Tool fuzzy-matches certificate page names to Google Sheet names with confidence scores
- [ ] **MTCH-02**: Tool displays dry-run preview table of matches before any action
- [ ] **MTCH-03**: Tool flags low-confidence matches for manual review
- [ ] **MTCH-04**: Tool lists unmatched attendees who have no certificate match

### Email

- [ ] **MAIL-01**: Tool asks for explicit confirmation before sending any emails
- [ ] **MAIL-02**: Tool sends certificate PDFs as email attachments via Gmail/SMTP
- [ ] **MAIL-03**: Tool handles per-send errors, logs sent/failed, and skips already-sent on re-run

### Configuration

- [x] **CONF-01**: API keys, SMTP credentials, and sheet ID are loaded from `.env` file
- [x] **CONF-02**: Tool returns meaningful exit codes (0 = success, 1 = partial failure, 2 = config error)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Email Enhancements

- **MAIL-04**: Progress bar during email send
- **MAIL-05**: Custom email subject/body template via Jinja2
- **MAIL-06**: Summary email digest sent to organizer at end of batch

### Matching Enhancements

- **MTCH-05**: Interactive match editor to remap wrong matches before send
- **MTCH-06**: Export match report to CSV for audit trail

### Configuration Enhancements

- **CONF-03**: Configurable divider page detection text (not just "Participantes")
- **CANV-05**: OCR-based name extraction as fallback strategy

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web UI / dashboard | CLI is sufficient; web adds disproportionate infrastructure |
| Certificate creation in Canva | Canva API doesn't support writing text into designs; pages already exist |
| Multi-event batch mode | Single-event use sufficient for v1; adds config complexity |
| SMTP provider abstraction (SendGrid, SES) | Gmail covers current use case |
| Auto-send without review | Wrong fuzzy match sends certificate to wrong person; always require confirmation |
| Real-time status page | Rich terminal output provides same value |
| Scheduling / cron integration | Users can use system cron directly |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CANV-01 | Phase 2 | Pending |
| CANV-02 | Phase 2 | Pending |
| CANV-03 | Phase 2 | Pending |
| CANV-04 | Phase 2 | Pending |
| GSHT-01 | Phase 3 | Pending |
| GSHT-02 | Phase 3 | Pending |
| MTCH-01 | Phase 3 | Pending |
| MTCH-02 | Phase 3 | Pending |
| MTCH-03 | Phase 3 | Pending |
| MTCH-04 | Phase 3 | Pending |
| MAIL-01 | Phase 4 | Pending |
| MAIL-02 | Phase 4 | Pending |
| MAIL-03 | Phase 4 | Pending |
| CONF-01 | Phase 1 | Complete |
| CONF-02 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

---
*Requirements defined: 2026-03-17*
*Last updated: 2026-03-17 after roadmap creation — traceability complete*
