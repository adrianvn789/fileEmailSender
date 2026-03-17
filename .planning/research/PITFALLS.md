# Pitfalls Research

**Domain:** CLI tool integrating Canva Connect API, Google Sheets API, and Gmail/SMTP for certificate distribution
**Researched:** 2026-03-17
**Confidence:** HIGH (Canva API structure), HIGH (gspread/Google Sheets), MEDIUM (Gmail SMTP), HIGH (fuzzy matching)

---

## Critical Pitfalls

### Pitfall 1: Canva API Does Not Expose Text Content from Design Pages

**What goes wrong:**
The project requirement is to "extract each certificate page's participant name from the design." Developers assume the Canva Connect API provides an endpoint to read text elements, page titles, or design element content. It does not. The API only returns design-level metadata (title, page count, timestamps, thumbnail) — not the text strings inside individual pages.

**Why it happens:**
The Canva API documentation does not lead with this limitation. Developers naturally assume a design API exposes design content. The API is built for asset sync, export, and autofill workflows — not design content reading.

**How to avoid:**
Decide on the name-extraction strategy before writing any Canva API integration code. Two viable approaches exist:
1. **Export pages as images (PNG) and run OCR** — export each page as a high-resolution PNG, then use `pytesseract` or Google Cloud Vision to extract the participant name text.
2. **Page naming convention** — if certificates are authored with the participant name as the Canva page title, the page title is accessible via the design pages list (page titles ARE returned as metadata). Validate this assumption against actual designs before coding.

If relying on page titles: confirm in the actual Canva design that each certificate page is titled with the participant name. If not titled this way, the OCR route is required.

**Warning signs:**
- Design pages API returns empty or generic page titles ("Page 1", "Page 2")
- No `text_elements` or `content` field in page API response
- Inability to programmatically distinguish certificate pages by name without exporting them

**Phase to address:**
Phase 1 (Canva API integration). Spike this assumption first — before building the matching pipeline.

---

### Pitfall 2: Canva Export Is Asynchronous — Treating It as Synchronous Breaks Everything

**What goes wrong:**
Developers call `POST /v1/exports` and immediately try to use the download URL from the response. The export job is asynchronous: the initial response returns a job ID with `status: "in_progress"`. The download URL only appears when status becomes `"success"`. Code that doesn't poll will get a `None` URL and crash or silently skip certificates.

**Why it happens:**
Most developers have experience with synchronous download APIs. The need to poll a separate status endpoint is easy to miss when skimming the docs.

**How to avoid:**
Implement a proper polling loop with exponential backoff from the start:
```python
import time

def wait_for_export(job_id, client, max_wait=120):
    interval = 2
    elapsed = 0
    while elapsed < max_wait:
        job = client.get_export_job(job_id)
        if job.status == "success":
            return job.urls
        if job.status == "failed":
            raise ExportError(job.error)
        time.sleep(interval)
        elapsed += interval
        interval = min(interval * 2, 30)  # exponential backoff, cap at 30s
    raise TimeoutError(f"Export job {job_id} did not complete in {max_wait}s")
```

**Warning signs:**
- `urls` field is `None` or missing in export response
- KeyError accessing download URL immediately after creating export job
- Intermittent certificate download failures (race condition)

**Phase to address:**
Phase 1 (Canva API integration). Build polling into the export helper from the start; retrofitting it is error-prone.

---

### Pitfall 3: Canva Export Rate Limits Will Throttle Large Certificate Runs

**What goes wrong:**
With many certificates (50+ attendees), the export pipeline hits Canva's rate limits and starts receiving `429` errors. The tool crashes or silently skips certificates. Rate limits are:
- 20 export creation requests per minute per user
- 75 exports per 5-minute window per user
- 75 exports per 5-minute window per design
- 5,000 exports per 24-hour window

**Why it happens:**
Developers build a simple loop that exports all pages as fast as possible without rate awareness.

**How to avoid:**
- Export one page at a time (using the `pages` parameter to specify a single page index per export job) rather than all pages at once — this gives finer control and retry granularity.
- Add a minimum delay between export creation calls (3-4 seconds minimum to stay under 20/minute).
- Handle `429` responses with a wait-then-retry strategy.
- Log progress so a failed mid-run can be resumed without re-exporting already-downloaded pages.

**Warning signs:**
- `HTTP 429` errors in logs during export creation loop
- Random export failures that succeed on retry
- Total run time growing non-linearly with attendee count

**Phase to address:**
Phase 1 (Canva API integration). Build rate-aware looping before testing with real designs.

---

### Pitfall 4: Fuzzy Matching False Positives Send Wrong Certificate to Wrong Person

**What goes wrong:**
The fuzzy matching score threshold is set too low (e.g., 70-80%), causing the tool to auto-confirm a match between "Maria Santos" (Google Sheet) and "Maria Silva" (Canva page). The wrong person receives the wrong certificate. This is a trust-destroying failure — worse than an unmatched certificate that gets flagged for review.

**Why it happens:**
Developers see 80% as "pretty good" without realizing short names with common words (Maria, José, Ana) can score high against wrong targets. The `ratio` scorer is also not optimal for name matching — it matches character-by-character without accounting for word order or partial names.

**How to avoid:**
- Use `token_sort_ratio` or `token_set_ratio` from RapidFuzz for name matching — these handle word-order differences and partial names better than plain `ratio`.
- Set a HIGH confidence threshold (90-95%) for auto-confirmation. Below that threshold, all matches must be flagged for manual review.
- Never auto-send without explicit human confirmation of flagged matches. The manual review output should show the Canva name and matched Google Sheet name side by side.
- Test the matcher against real certificate name lists before first production run.

**Warning signs:**
- Match scores clustering around 80-85% for known-different names
- Short names (2-3 characters) matching incorrectly
- Names with shared first names but different surnames getting high scores

**Phase to address:**
Phase 2 (matching pipeline). Invest time validating threshold with real data before enabling auto-send.

---

### Pitfall 5: Gmail App Password or SMTP Auth Fails Silently or With Confusing Error

**What goes wrong:**
Using a regular Gmail password for SMTP authentication fails because Google has disabled basic auth for Gmail accounts. The error is `SMTPAuthenticationError` with a message referencing "App Passwords" — which confuses developers who haven't set one up. Alternatively, the developer uses an App Password but hasn't enabled 2-Step Verification first (App Passwords are only available with 2FA enabled).

**Why it happens:**
Google deprecated less-secure app access. Many Python SMTP tutorials predate this change and show plain password usage.

**How to avoid:**
- Gmail SMTP requires a 16-character App Password, not the account password.
- App Passwords require Google 2-Step Verification to be enabled on the sending account.
- Store the App Password in a `.env` file, never in source code. Load it with `python-dotenv`.
- Use port 587 with STARTTLS (`smtplib.SMTP` + `starttls()`) or port 465 with SSL (`smtplib.SMTP_SSL`). Do not use port 25.

**Warning signs:**
- `SMTPAuthenticationError: (535, b'5.7.8 Username and Password not accepted')`
- Missing "App passwords" option in Google account security settings (2FA not enabled)
- `SMTPException: SMTP AUTH Extension Not Supported by Server` when using wrong port/TLS setup

**Phase to address:**
Phase 3 (email sending). Document the App Password setup requirement clearly in the project README as a prerequisite.

---

### Pitfall 6: Google Sheets Service Account Not Shared with the Sheet

**What goes wrong:**
The service account is created, credentials JSON is downloaded, `gspread` authenticates successfully — but every attempt to open the spreadsheet raises `SpreadsheetNotFound` or `APIError: 403 PERMISSION_DENIED`. The spreadsheet exists; the account just can't see it.

**Why it happens:**
Service accounts are separate Google accounts. They have no access to any spreadsheet unless explicitly granted. Developers create the service account and assume it inherits their own Google Drive access.

**How to avoid:**
Share the target Google Sheet with the service account's `client_email` (found in the credentials JSON), granting at least "Viewer" access. This is a one-time manual step per sheet.

**Warning signs:**
- `gspread.exceptions.SpreadsheetNotFound` despite the spreadsheet ID being correct
- `APIError: [403]: The caller does not have permission`
- Script works after sharing but fails on a new sheet that wasn't shared

**Phase to address:**
Phase 2 (Google Sheets integration). Include this step explicitly in setup documentation.

---

### Pitfall 7: Credentials and Secrets Committed to Version Control

**What goes wrong:**
The Google service account JSON credentials file, Gmail App Password, or Canva OAuth tokens are hardcoded in the Python script or committed to the git repository. Anyone with repository access can impersonate the service account, send emails from the Gmail account, or access Canva designs.

**Why it happens:**
CLI scripts feel "personal" — developers don't treat them with the same security discipline as web applications. Getting things working quickly leads to hardcoded credentials.

**How to avoid:**
- Store ALL secrets in a `.env` file: `CANVA_ACCESS_TOKEN`, `GMAIL_APP_PASSWORD`, `GOOGLE_CREDENTIALS_PATH`, `SPREADSHEET_ID`.
- Add `.env` and `credentials.json` (or similar) to `.gitignore` before the first commit.
- Use `python-dotenv` to load secrets at runtime.
- Provide a `.env.example` file with placeholder values for documentation.

**Warning signs:**
- String literals containing API keys or passwords in `.py` files
- `credentials.json` or `token.json` appearing in `git status` as tracked files
- No `.gitignore` present in the repo root

**Phase to address:**
Phase 0 (project setup). Set up `.env` pattern before writing any integration code.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode Canva design ID in script | No config needed | Must edit source code for each event | Never — use CLI arg or `.env` |
| Export all pages then filter | Simpler loop logic | Wastes Canva export quota on non-certificate pages | Never — export only pages after divider |
| Auto-confirm all fuzzy matches above 70% | Faster runs | Wrong certificates sent to wrong people | Never |
| Skip error handling on export failures | Less code | Silently drops certificates without warning | Never |
| Single SMTP connection for all emails | Simpler code | Connection timeout on large batches | MVP acceptable if <50 recipients |
| No dry-run mode | Faster to build | Cannot validate matching without sending real emails | Never — dry-run is essential for safety |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Canva API | Assuming design API returns text content of elements | Text content is not exposed; use page titles (if present) or OCR on exported images |
| Canva API | Treating export as synchronous | Always poll the Get Export Job endpoint until status is `"success"` |
| Canva API | Not specifying the `pages` parameter | Omitting `pages` exports ALL pages as one multi-page PDF; specify single page index per export |
| Canva API | Access token expiry (4 hours) | Implement token refresh; store refresh token alongside access token |
| Canva API | `design:content:read` scope not requested | Missing scope causes `403` on design read — verify required scopes in Developer Portal |
| Google Sheets | Sharing spreadsheet with own Google account, not service account | Must share with service account `client_email` from credentials JSON |
| Google Sheets | gspread v6 breaking changes — `get_records()` removed | Use `get_all_records()` or manual fetch; check installed gspread version |
| Google Sheets | Reading cells one by one in a loop | Use `get_all_values()` or `get_all_records()` for a single batch read |
| Gmail SMTP | Using regular Gmail password | Must use App Password (requires 2FA) or OAuth2 |
| Gmail SMTP | Port mismatch | Use port 587 with STARTTLS or port 465 with SSL — not port 25 |
| Gmail SMTP | Attaching PDF without specifying MIME type | Use `application/pdf` MIME type; plain `application/octet-stream` may be filtered |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Export all pages sequentially without rate limiting | `429` errors mid-run, incomplete certificate set | Add 3-4 second delay between export requests; implement retry | ~20+ attendees in a single run |
| Downloading export URLs after they expire | `403` or `404` on download | Download immediately after export job succeeds; URLs expire in 24 hours | If script pauses overnight between export and download |
| Making multiple gspread API calls per row | Slow reads, `429` rate limiting from Sheets API | Read entire sheet in one call with `get_all_records()` | ~60 rows (Sheets API limit: 60 requests/minute/user) |
| Opening SMTP connection per email | Slow sending, connection errors on large batches | Use `with smtplib.SMTP(...) as smtp:` and reuse for all messages | 20+ emails in quick succession |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing credentials JSON to git | Full service account compromise; access to all shared sheets | `.gitignore` credentials JSON before first commit; rotate key if leaked |
| Storing Gmail App Password in source code | Email account compromise; spam sending | Use `.env` file + `python-dotenv`; never hardcode |
| Storing Canva tokens in source code | Access to all Canva designs in the workspace | Use `.env` file; treat tokens as passwords |
| Logging email addresses or names to console unconditionally | PII exposure in logs/terminals in shared environments | Use `--verbose` flag to gate PII logging; default to summary only |
| No confirmation step before sending | Accidental mass send to wrong recipients | Require explicit `--send` flag; default to dry-run that shows what would be sent |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No dry-run mode | User cannot verify matches before sending real emails | Default to dry-run; require `--send` flag to actually send |
| Silent failure on unmatched certificates | Some attendees never receive their certificate without knowing why | Print a clear unmatched list at end of run; exit with non-zero code if any are unmatched |
| Cryptic error messages from Canva/gspread exceptions | User cannot diagnose auth or permission issues | Catch known exceptions and print human-readable remediation steps |
| No progress output during export polling | User thinks the tool hung during long export waits | Print progress ("Exporting certificate 3/47... waiting for job abc123") |
| No summary at end of run | User cannot tell if the run succeeded or what was skipped | Print a final summary: N sent, M skipped (unmatched), P errors |

---

## "Looks Done But Isn't" Checklist

- [ ] **Canva page name extraction:** Verify page titles in the actual design contain participant names — not generic "Page 1" labels — before assuming this approach works
- [ ] **Fuzzy matching:** Tested against real attendee name data (not synthetic names) — edge cases include accents, middle names, nicknames, and honorifics
- [ ] **Export single pages:** Confirm `pages` parameter exports one page as a single-page PDF (not a slice of a multi-page PDF that email clients may display oddly)
- [ ] **Gmail send limits:** Verified the sending account has not hit the 100-email-per-day SMTP limit before a large run
- [ ] **Dry-run mode:** Exists and prints exactly what would be sent (certificate filename, matched name, recipient email) before any real sending
- [ ] **Unmatched certificates:** Clearly reported with the Canva page name, not silently discarded
- [ ] **Canva token refresh:** If running on a schedule or long pipeline, access token expiry (4 hours) is handled
- [ ] **`.gitignore`:** Includes `.env`, `credentials.json`, `token.json`, `*.pdf` (downloaded certificates should not be committed)

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong certificate sent to recipient | HIGH | Manually contact affected recipients; re-send correct certificate; apologize; audit the full match list |
| Credentials committed to git | HIGH | Immediately revoke/rotate service account key in Google Cloud Console; revoke Gmail App Password; regenerate Canva tokens; remove from git history with `git filter-branch` or BFG |
| Export rate limit hit mid-run | LOW | Wait for rate limit window to reset (~5 minutes); resume from last successfully downloaded certificate |
| Spreadsheet not shared with service account | LOW | Share spreadsheet with service account `client_email`; re-run |
| gspread `get_records()` removed (v6 upgrade) | LOW | Replace with `get_all_records()` or manual fetch pattern |
| Export jobs failing for specific pages | MEDIUM | Check if design contains premium/licensed elements (`license_required` error); export those pages manually from Canva UI |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Canva API has no text content endpoint | Phase 1 — spike page title approach on real design before building matching | Confirm page titles contain participant names; if not, design OCR fallback |
| Async export not handled | Phase 1 — build polling into export helper | Verify export helper returns download URL, not raw job response |
| Export rate limits | Phase 1 — add delay and retry to export loop | Run a batch of 25 exports and confirm no 429 errors |
| Fuzzy matching false positives | Phase 2 — validate threshold with real name data | Test with intentionally similar but wrong name pairs from actual past event data |
| Gmail App Password setup | Phase 3 — document prerequisite; test auth before main pipeline | Confirm a test email sends successfully before wiring into main loop |
| Service account not shared with sheet | Phase 2 — include share step in setup docs; test read before pipeline | Confirm `get_all_records()` returns data before building matching logic |
| Credentials committed to VCS | Phase 0 — create `.gitignore` before first code commit | Run `git status` and confirm no `.env` or JSON credential files appear |
| No dry-run mode | Phase 3 — build dry-run as default; `--send` as opt-in | Verify dry-run output lists correct matches without sending any email |

---

## Sources

- Canva Connect API — Export endpoint reference: https://www.canva.dev/docs/connect/api-reference/exports/create-design-export-job/
- Canva Connect API — Requests & responses (polling, rate limits): https://www.canva.dev/docs/connect/api-requests-responses/
- Canva Connect API — Authentication and OAuth scopes: https://www.canva.dev/docs/connect/authentication/
- Canva Connect API — Documentation index (confirmed no text-content endpoints): https://www.canva.dev/docs/connect/llms.txt
- gspread documentation — Authentication: https://docs.gspread.org/en/latest/oauth2.html
- gspread documentation — Usage guide (rate limits, batch reads): https://docs.gspread.org/en/latest/user-guide.html
- gspread — HISTORY.rst (v6 breaking changes): https://github.com/burnash/gspread/blob/master/HISTORY.rst
- RapidFuzz — False positives in fuzzy name matching: https://github.com/rapidfuzz/RapidFuzz
- Gmail SMTP App Password requirement: https://www.pythontutorials.net/blog/cant-send-email-via-python-using-gmail-smtplib-smtpexception-smtp-auth-extension-not-supported-by-server/
- Gmail bulk sending limits and 2025 enforcement: https://powerdmarc.com/gmail-enforcement-email-rejection/

---
*Pitfalls research for: Canva certificate sender CLI (Canva API + Google Sheets API + Gmail SMTP)*
*Researched: 2026-03-17*
