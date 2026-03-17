# Canva Certificate Sender

## What This Is

A Python CLI tool that connects to the Canva API, extracts individual certificate pages from a multi-page design, matches them to attendees listed in a Google Sheet using fuzzy name matching, and emails each person their certificate as a PDF via Gmail/SMTP.

## Core Value

Automate the tedious process of extracting, matching, and emailing personalized event attendance certificates from Canva to attendees.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Connect to Canva API and access a workspace design by ID
- [ ] Parse multi-page design, identify certificate pages after the "Participantes" divider page
- [ ] Extract each certificate page's participant name from the design
- [ ] Export each certificate page as PDF via Canva API
- [ ] Read attendee list (name + email) from a Google Sheet
- [ ] Fuzzy match certificate page names to Google Sheet names
- [ ] Flag unmatched/low-confidence matches for manual review
- [ ] Send matched certificates as PDF attachments via Gmail/SMTP
- [ ] CLI interface to run the full pipeline from terminal

### Out of Scope

- Web UI — CLI only for v1
- Certificate template design/creation — templates already exist in Canva
- OAuth social login — not a user-facing app
- Batch creation of certificates in Canva — pages already exist

## Context

- Certificates are for event attendance (workshops, conferences, etc.)
- One Canva design contains all certificates as separate pages
- A divider page with the string "Participantes" separates non-certificate pages from certificate pages
- Each certificate page has the attendee's name on it, but it may not exactly match the name in the Google Sheet (typos, partial names, abbreviations)
- The Google Sheet contains two key columns: attendee name and email address
- Python chosen for its strong ecosystem of API client libraries (requests, gspread, etc.)

## Constraints

- **Tech stack**: Python CLI script
- **Canva API**: Must use Canva Connect API for design access and PDF export
- **Google Sheets**: Must use Google Sheets API (via gspread or similar) for attendee data
- **Email**: Gmail/SMTP for sending certificates
- **Matching**: Fuzzy string matching needed due to name discrepancies between Canva and Google Sheet

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python CLI | User preference + strong library ecosystem for APIs and Google Sheets | — Pending |
| Gmail/SMTP for email | User's preferred sending method | — Pending |
| Fuzzy matching with manual review | Names may not match exactly; flag uncertain matches for human review | — Pending |
| "Participantes" page as divider | Existing convention in user's Canva designs to separate certificate pages | — Pending |

---
*Last updated: 2026-03-17 after initialization*
