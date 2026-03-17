# Stack Research

**Domain:** Python CLI tool — Canva API + Google Sheets + Gmail/SMTP certificate distribution
**Researched:** 2026-03-17
**Confidence:** MEDIUM (Canva Connect API has a critical undocumented gap — see pitfall below)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | Stable, widely-deployed, supported by all libraries below. 3.12 is acceptable; avoid 3.9/3.10 as Click 8.3.x requires >=3.10 and newer Python improves type hint ergonomics. |
| Click | 8.3.1 | CLI framework | Mature, decorator-based, battle-tested for pipeline CLIs. Simpler than Typer for a single-command script that doesn't need auto-generated docs. Requires Python >=3.10. |
| requests | 2.32.5 | HTTP client for Canva API | No official Canva Python SDK exists. Canva provides an OpenAPI spec and recommends using openapi-generator — but for a small CLI, raw requests is simpler and more readable than a generated client. |
| gspread | 6.2.1 | Google Sheets reader | The standard Python library for Google Sheets. Service account auth works headlessly (no browser required), which is essential for a CLI pipeline. Requires Python >=3.8. |
| google-auth | 2.49.1 | Google OAuth credentials | Required by gspread for service account authentication. google-auth handles credential refresh automatically. |
| rapidfuzz | 3.14.3 | Fuzzy name matching | Drop-in replacement for fuzzywuzzy, MIT-licensed (fuzzywuzzy uses GPL), C++ backend so significantly faster, and has more matching algorithms. Use `process.extractOne()` with a score threshold. |
| python-dotenv | 1.2.2 | Credential management | Keeps secrets (Canva client ID/secret, token storage path, SMTP password) out of source code and out of environment variable ceremony for users. |
| rich | 14.3.3 | CLI output formatting | Makes the matching review table and progress output readable without much code. Especially useful for the manual review step where mismatches need to be clearly visible. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pypdf | 6.9.1 | PDF text extraction | CRITICAL: The Canva Connect API does not return page names or text content. The only viable way to extract participant names from certificate pages is to export each page as a single-page PDF and then extract text from it. Use `pypdf` to read the name text from each exported single-page PDF before sending. |
| smtplib | stdlib | SMTP email sending | Built into Python standard library. Sufficient for Gmail/SMTP with app passwords. No extra install needed. |
| email (EmailMessage) | stdlib | Email message construction | Python stdlib. Use `email.message.EmailMessage` with `make_alternative()` for attaching PDFs. No extra install needed. |
| keyring | 25.6.1 | Secure token storage | Optional but recommended. Stores the Canva OAuth refresh token in the OS keychain rather than a plaintext file. Avoids re-authorizing on every run. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Fast package manager and virtual env | Replaces `pip` + `venv`. Install with `curl -Ls https://astral.sh/uv/install.sh | sh`. Use `uv sync` and `uv run` rather than activating venvs manually. |
| ruff | Linter and formatter | Single tool replaces flake8 + black + isort. Zero-config for standard Python projects. |
| pytest | Test runner | Standard. Use with `pytest-mock` for mocking API calls. |

## Installation

```bash
# Using uv (recommended)
uv init canva-cert-sender
cd canva-cert-sender
uv add click requests gspread google-auth rapidfuzz python-dotenv rich pypdf keyring

# Dev dependencies
uv add --dev ruff pytest pytest-mock

# OR using pip
pip install click requests gspread google-auth rapidfuzz python-dotenv rich pypdf keyring
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Click 8.3.1 | Typer 0.24.1 | Prefer Typer if you want auto-generated `--help` docs from type hints, or if this CLI will grow into a multi-command tool with subcommands. For a single pipeline command, Click's decorator style is more explicit and widely understood. |
| requests 2.32.5 | httpx 0.28.1 | Use httpx if you need async HTTP (e.g., parallel PDF exports). For this sequential pipeline, requests is simpler and has no async overhead. |
| requests 2.32.5 | openapi-generator SDK | Canva recommends generating an SDK from their OpenAPI spec. Only worth the setup cost if the project grows to use many Canva endpoints. For 3-4 endpoints, raw requests is cleaner. |
| gspread 6.2.1 | google-api-python-client | gspread is a purpose-built abstraction over the Sheets API. The raw google-api-python-client requires more boilerplate for simple read operations. |
| pypdf 6.9.1 | pdfminer.six 20260107 | Use pdfminer.six if pypdf fails to extract text from Canva-generated PDFs (some PDFs encode text in ways that confuse simple extractors). pdfminer.six has more robust layout analysis. Treat it as a fallback. |
| rapidfuzz 3.14.3 | fuzzywuzzy | Never use fuzzywuzzy for new projects. It is GPL-licensed (forcing your code to be GPL), slower, and has known bugs in `partial_ratio`. rapidfuzz is its stated successor and drop-in replacement. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| fuzzywuzzy | GPL license contaminates your project; has known `partial_ratio` bugs; unmaintained. rapidfuzz was created explicitly to replace it. | rapidfuzz |
| PyMuPDF (fitz) | AGPL licensed — forces open-sourcing if distributed. Strong text extraction but license is prohibitive for most projects. | pypdf (MIT), fallback to pdfminer.six (MIT) |
| Typer for this specific CLI | Adds a Rich/Typer dependency tree (Typer bundles its own Rich); minor added complexity for a single-entrypoint script. | Click + rich installed separately |
| requests-oauthlib | Adds abstraction over OAuth that obscures the Canva-specific PKCE flow. Canva PKCE requires custom code_verifier/code_challenge generation regardless — so this library saves little and adds a dependency. | Implement PKCE manually with hashlib + base64 (stdlib); exchange tokens via raw requests calls. |
| .env file for token storage | OAuth refresh tokens in a .env file are readable by any process. | keyring for token storage, .env only for non-secret config (sheet ID, design ID). |

## Stack Patterns by Variant

**If PDF text extraction fails (Canva encodes text as paths/shapes):**
- Fall back to pdfminer.six instead of pypdf for the name extraction step
- If both fail, use thumbnail OCR: Canva's get-design-pages endpoint returns thumbnail URLs. Download the thumbnail, run pytesseract (Tesseract OCR wrapper) to extract the name visually
- Treat OCR as last resort — it requires the Tesseract binary installed on the host machine

**If the user re-runs the script for the same design:**
- Cache the OAuth token via keyring so re-authorization is not required
- Cache matched pairs (name -> email) in a local JSON file keyed by design_id to skip re-matching

**If SMTP authentication fails with Gmail:**
- Gmail requires an "App Password" (not the account password) when 2FA is enabled
- Alternatively, use the Gmail API (via google-api-python-client) for more reliable sending
- smtp.gmail.com port 587 with STARTTLS is the correct configuration

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Click 8.3.1 | Python >=3.10 | Breaking change from Click 7.x: `@click.command` decorator API is stable. |
| gspread 6.2.1 | google-auth >=2.0.0 | gspread v6 dropped support for oauth2client; must use google-auth. If you see oauth2client errors, you are on an old gspread. |
| rapidfuzz 3.14.3 | Python >=3.9 | C extension wheels available for 3.9–3.14. Falls back to pure Python on unsupported platforms. |
| pypdf 6.9.1 | Python >=3.9 | API changed from PyPDF2 (deprecated); import as `from pypdf import PdfReader`. |

## Critical Feasibility Note (HIGH confidence — verified against official docs)

**The Canva Connect API does not expose page names or text content.**

The `GET /v1/designs/{designId}/pages` endpoint returns only: `index`, `dimensions`, and `thumbnail`. There is no text content field, no page title, and no way to read the participant name from a design page via the API.

**Implication for architecture:** The participant name extraction step must use one of:

1. **PDF text extraction (recommended first attempt):** Export each page as a single-page PDF (`pages: [N]` in the export job request), then extract text using pypdf. Works if Canva encodes text as selectable text (likely for standard text boxes).
2. **OCR on thumbnails (fallback):** Download the thumbnail URL returned by get-pages, run pytesseract on it. Slower, requires Tesseract binary, lower accuracy.
3. **Manual mapping (escape hatch):** Export all pages as individual PDFs named `page_1.pdf`, `page_2.pdf`, etc., then let the user provide a CSV mapping page numbers to names. Not automated but reliable.

The recommended approach is #1 (PDF text extraction via pypdf). This should be validated early in the project before committing to the full pipeline.

**Canva OAuth is OAuth 2.0 PKCE — not API keys.** This means the first run requires a browser authorization step. For a CLI tool, you open the auth URL, the user approves in browser, then pastes the callback URL (or code) back into the terminal. Store the refresh token via keyring for subsequent runs.

## Sources

- PyPI: gspread 6.2.1 — https://pypi.org/project/gspread/ (MEDIUM confidence — version verified)
- PyPI: rapidfuzz 3.14.3 — https://pypi.org/project/rapidfuzz/ (HIGH confidence — version verified, license verified)
- PyPI: Click 8.3.1 — https://pypi.org/project/click/ (HIGH confidence — version verified)
- PyPI: Typer 0.24.1 — https://pypi.org/project/typer/ (HIGH confidence — version verified)
- PyPI: requests 2.32.5 — https://pypi.org/project/requests/ (HIGH confidence — version verified)
- PyPI: python-dotenv 1.2.2 — https://pypi.org/project/python-dotenv/ (HIGH confidence — version verified)
- PyPI: rich 14.3.3 — https://pypi.org/project/rich/ (HIGH confidence — version verified)
- PyPI: pypdf 6.9.1 — https://pypi.org/project/pypdf/ (HIGH confidence — version verified)
- PyPI: pdfminer.six 20260107 — https://pypi.org/project/pdfminer.six/ (HIGH confidence — version verified)
- PyPI: google-auth 2.49.1 — https://pypi.org/project/google-auth/ (HIGH confidence — version verified)
- Canva Connect API — Authentication: https://www.canva.dev/docs/connect/authentication/ (HIGH confidence — OAuth PKCE confirmed as only auth method)
- Canva Connect API — Export endpoint: https://www.canva.dev/docs/connect/api-reference/exports/create-design-export-job/ (HIGH confidence — per-page PDF export confirmed, `pages` parameter documented)
- Canva Connect API — Get design pages: https://www.canva.dev/docs/connect/api-reference/designs/get-design-pages/ (HIGH confidence — confirmed no page names/text in response)
- Canva Connect API — Get design: https://www.canva.dev/docs/connect/api-reference/designs/get-design/ (HIGH confidence — confirmed metadata-only response, no text content)
- Canva Connect API — No Python SDK: https://www.canva.dev/docs/connect/ (HIGH confidence — Canva states openapi-generator for SDK generation, no pre-built Python library)
- gspread docs — Service account auth: https://docs.gspread.org/en/latest/ (MEDIUM confidence — service_account() shown as primary pattern)

---
*Stack research for: Canva Certificate Sender CLI*
*Researched: 2026-03-17*
