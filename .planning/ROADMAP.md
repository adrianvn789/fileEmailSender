# Roadmap: Canva Certificate Sender

## Overview

Four phases that build a CLI pipeline end-to-end: first establish the project skeleton and credential safety baseline, then validate the highest-risk assumption (Canva name extraction) before writing matching logic, then wire Google Sheets data into a dry-run matching preview, then add the email send layer with all safety gates. Each phase delivers a verifiable capability; no phase is just scaffolding or task accumulation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Setup and Security Baseline** - Project skeleton, credential hygiene, data models, pure matcher logic with tests
- [ ] **Phase 2: Canva Integration** - OAuth PKCE, design page listing, divider detection, PDF export, name extraction validation
- [ ] **Phase 3: Sheets Integration and Matching Pipeline** - Read attendee data, fuzzy match, dry-run preview table, unmatched report
- [ ] **Phase 4: Email Send Pipeline** - SMTP send with PDF attachment, confirmation gate, error handling, idempotency, CLI entry point

## Phase Details

### Phase 1: Setup and Security Baseline
**Goal**: The project is safe to develop — credentials can never be committed, the dependency stack is locked, core data models are defined, and the matcher is fully unit-tested against real name data before any API call is made.
**Depends on**: Nothing (first phase)
**Requirements**: CONF-01, CONF-02
**Success Criteria** (what must be TRUE):
  1. Running the CLI with a missing `.env` variable exits with code 2 and a human-readable error message identifying which variable is missing
  2. `.gitignore` prevents `.env`, `credentials.json`, `token.json`, and any `*.pdf` files from being staged by git
  3. `uv run pytest` passes with unit tests covering the fuzzy matcher at multiple confidence levels (high-confidence match, below-threshold match, no match)
  4. `Certificate`, `Attendee`, `MatchResult`, and `PipelineResult` dataclasses exist and can be instantiated without error
**Plans:** 1 plan
Plans:
- [ ] 01-01-PLAN.md — Project scaffold, credential safety, data models, fuzzy matcher, and full test suite

### Phase 2: Canva Integration
**Goal**: The tool can authenticate with Canva, list all pages of a design, isolate certificate pages after the "Participantes" divider, extract a participant name from each certificate page, and export each page as a PDF — with the name extraction strategy empirically validated against a real design.
**Depends on**: Phase 1
**Requirements**: CANV-01, CANV-02, CANV-03, CANV-04
**Success Criteria** (what must be TRUE):
  1. Given a valid design ID in `.env`, the tool prints a numbered list of page names returned by the Canva API
  2. The tool correctly identifies and skips all pages before and including the "Participantes" divider, printing only certificate pages
  3. The tool extracts a participant name string from each certificate page (via page title or PDF text extraction) and the name matches what is visible on the certificate
  4. For each certificate page, the tool creates a Canva export job, polls until complete, and saves a single-page PDF to a temp directory — without hitting a rate limit error on a design of at least 10 pages
**Plans**: TBD

### Phase 3: Sheets Integration and Matching Pipeline
**Goal**: The tool reads the attendee list from a Google Sheet, fuzzy-matches each certificate page name to an attendee, and produces a dry-run preview table showing every match with confidence scores — surfacing low-confidence matches and unmatched attendees before any email is sent.
**Depends on**: Phase 2
**Requirements**: GSHT-01, GSHT-02, MTCH-01, MTCH-02, MTCH-03, MTCH-04
**Success Criteria** (what must be TRUE):
  1. The tool reads name and email columns from a Google Sheet using a service account, and the user can configure which column indices contain name and email without editing source code
  2. Running the tool in dry-run mode (default) prints a Rich table with columns: certificate page name | matched attendee name | email | confidence score
  3. Matches below the confidence threshold are visually flagged in the table and listed separately for manual review before any action is taken
  4. Attendees with no matching certificate page are listed in a separate "unmatched" section of the output
**Plans**: TBD

### Phase 4: Email Send Pipeline
**Goal**: The tool can send each matched certificate as a PDF email attachment via Gmail SMTP, with an explicit confirmation gate before sending, per-email error handling, and idempotency so re-runs after partial failures do not double-send.
**Depends on**: Phase 3
**Requirements**: MAIL-01, MAIL-02, MAIL-03
**Success Criteria** (what must be TRUE):
  1. Without the `--send` flag, the tool completes the full pipeline and exits without sending any email — the dry-run default cannot be bypassed accidentally
  2. With `--send`, the tool prints the full match table and requires an explicit Y confirmation before the first email is dispatched
  3. A received email contains the correct attendee name in the subject, and the PDF attachment opens to the correct certificate page
  4. If one SMTP send fails mid-batch, the tool logs the failure, continues sending remaining certificates, and exits with code 1; re-running skips already-sent recipients and only retries failed ones
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Setup and Security Baseline | 0/1 | Planning complete | - |
| 2. Canva Integration | 0/TBD | Not started | - |
| 3. Sheets Integration and Matching Pipeline | 0/TBD | Not started | - |
| 4. Email Send Pipeline | 0/TBD | Not started | - |
