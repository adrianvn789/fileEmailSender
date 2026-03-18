# Phase 2: Canva Integration - Research

**Researched:** 2026-03-18
**Domain:** Canva Connect API — OAuth PKCE, design page listing, text extraction via PDF, export pipeline
**Confidence:** MEDIUM (API surface confirmed via official docs; text extraction strategy requires empirical validation against real design)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Names are in a **specific textbox element** on each certificate page — use the Canva API to read text elements from design pages to extract participant names
- The "Participantes" divider is a page with a single textbox containing the word "Participantes" — detection uses **contains** logic (case-insensitive substring match on text elements), not exact page title match
- All pages before and including the divider are skipped; certificate pages come after it

### Claude's Discretion
- **Auth flow**: OAuth 2.0 PKCE implementation, browser redirect handling, token storage and refresh strategy
- **Which textbox holds the name**: Heuristic for identifying the name textbox among potentially multiple textboxes on a certificate page (e.g., largest text, specific position, filtering out static labels)
- **Export strategy**: Async export job creation, polling interval, concurrency, rate limit handling
- **Error handling**: API error retries, timeout handling, partial failure recovery
- **Module structure**: How to organize the Canva API client code within the existing `src/canva_client/` package
- **Design ID input**: How the user provides the Canva design ID (already in `.env` as noted in success criteria)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CANV-01 | User can connect to Canva API and list pages of a design by ID | OAuth PKCE flow + `GET /v1/designs/{id}/pages` endpoint confirmed |
| CANV-02 | Tool detects the "Participantes" divider page and isolates certificate pages after it | Requires text element extraction from pages — PDF-based strategy documented below |
| CANV-03 | Tool extracts the participant name from each certificate page | PDF export + pdfplumber extraction is the viable path — Canva Connect API has no direct text element endpoint |
| CANV-04 | Tool exports each matched certificate page as a PDF via Canva export API | `POST /v1/exports` with `pages` array + polling confirmed; rate limits documented |
</phase_requirements>

---

## Summary

The Canva Connect API uses OAuth 2.0 Authorization Code flow with PKCE. For a CLI tool, this means spinning up a local HTTP server on `http://127.0.0.1` to capture the redirect, then exchanging the code for tokens. Access tokens expire in 4 hours (`expires_in: 14400`); a refresh token is included and should be persisted between runs.

**Critical finding on text extraction:** The `GET /v1/designs/{id}/pages` endpoint returns only structural metadata — page index, dimensions, and a thumbnail URL. It does NOT return page titles or text element content. The Canva Connect API has no endpoint for reading text element content from design pages. The Content Querying API that can read text is part of the Apps SDK (runs inside Canva's browser sandbox), not the Connect API. Therefore, the locked decision to "use the Canva API to read text elements" cannot be implemented via a direct REST endpoint. The only viable path within the Connect API is: export each page as PDF, then use pdfplumber to extract text from the downloaded PDF bytes to identify the divider and extract participant names.

**Primary recommendation:** Export all pages as a single PDF job (pages 1..N), iterate through pages in the downloaded PDF using pdfplumber, detect the divider page by checking for "participantes" substring (case-insensitive), then extract the largest/most prominent text from each subsequent page as the participant name.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | HTTP client for Canva REST API calls | Async-capable, cleaner API than requests, supports streaming; already recommended pattern in the project ecosystem |
| pdfplumber | 0.11.9 | Extract text from exported certificate PDFs | Already installed in the project env; built on pdfminer.six; exposes per-character position data for heuristic name extraction |
| keyring | 25.7.0 | Persistent token storage across CLI runs | macOS Keychain / Linux Secret Service integration; avoids token re-auth on every run |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| http.server (stdlib) | — | Local redirect server for OAuth PKCE callback | Required for the auth flow — captures `?code=` from browser redirect |
| webbrowser (stdlib) | — | Opens system browser to Canva auth URL | Opens the Canva consent page without user needing to copy a URL |
| hashlib + base64 (stdlib) | — | Generate PKCE code_verifier and code_challenge | Pure stdlib — no external dep needed |
| asyncio (stdlib) | — | Async polling of export jobs | Enables concurrent poll loops without blocking |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pdfplumber | pypdf | pdfplumber provides character-level position data; pypdf gives raw text only — position data needed for name heuristic |
| keyring | Plain .env file | keyring is safer (tokens not in plaintext files); .env is simpler but exposes tokens |
| httpx | requests | httpx has async support and cleaner typing; requests is sync-only |

**Installation:**
```bash
uv add "httpx>=0.28.1" "pdfplumber>=0.11.9" "keyring>=25.7.0"
```

**Version verification:** Confirmed against PyPI registry on 2026-03-18.
- httpx: 0.28.1 (latest)
- pdfplumber: 0.11.9 (already installed in project env)
- keyring: 25.7.0 (latest)

## Architecture Patterns

### Recommended Project Structure
```
src/canva_client/
├── config.py         # existing — add CANVA_DESIGN_ID env var
├── models.py         # existing — Certificate dataclass
├── matcher.py        # existing — reuse normalize_name()
├── cli.py            # existing — add canva subcommand/pipeline step
├── auth.py           # NEW: OAuth PKCE flow, token storage/refresh
├── canva_api.py      # NEW: API client wrapping httpx calls
├── pages.py          # NEW: list pages, detect divider, filter certificates
└── exporter.py       # NEW: export jobs, polling, PDF download
```

### Pattern 1: OAuth PKCE for CLI
**What:** Spin up a temporary `http.server` on a random local port, open browser to Canva auth URL with `code_challenge`, capture the redirect `?code=` parameter, exchange for tokens, store with keyring, shut down server.
**When to use:** First run and whenever the stored refresh token is expired or missing.
**Example:**
```python
# Source: https://www.canva.dev/docs/connect/authentication/
import hashlib, base64, secrets, http.server, webbrowser, urllib.parse

def generate_pkce():
    verifier = secrets.token_urlsafe(96)[:128]  # 43-128 chars, URL-safe
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge

# Authorization URL params:
# client_id, response_type=code, scope, redirect_uri,
# code_challenge, code_challenge_method=S256, state
```

### Pattern 2: Token Lifecycle
**What:** Store `access_token` + `refresh_token` + `expires_at` in keyring under service name `canva-client`. On each API call, check if access token is expired; if so, use refresh token to get a new access token via `POST /v1/oauth/token` with `grant_type=refresh_token`.
**When to use:** Every API call — gate all requests through a token provider function.
**Example:**
```python
# Source: https://deepwiki.com/canva-sdks/canva-connect-api-starter-kit/2.2-authentication-and-authorization
# Token endpoint: POST https://api.canva.com/rest/v1/oauth/token
# Auth header: Basic base64(client_id:client_secret)
# Body: grant_type=refresh_token&refresh_token=<token>
# Response: { access_token, refresh_token, token_type, expires_in: 14400, scope }
```

### Pattern 3: Export + Text Extract for Name/Divider Detection
**What:** Export the full design as a PDF (all pages in one job), download the PDF bytes in memory, open with pdfplumber, iterate pages to find the divider and extract names.
**When to use:** This is the only viable path — the Connect API has no text element read endpoint.
**Example:**
```python
# Source: https://github.com/jsvine/pdfplumber
import pdfplumber, io, httpx

async def extract_page_texts(pdf_bytes: bytes) -> list[str]:
    """Returns extracted text for each page (1-indexed aligned to Canva page index)."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]

def find_divider_index(page_texts: list[str]) -> int:
    """Returns 0-based index of the Participantes divider page, or -1 if not found."""
    for i, text in enumerate(page_texts):
        if "participantes" in text.lower():
            return i
    return -1

def extract_name(text: str) -> str:
    """Heuristic: return the longest non-empty line as the participant name."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return max(lines, key=len) if lines else ""
```

### Pattern 4: Export Job with Polling
**What:** POST a single export job for the whole design (PDF format), then poll GET until status is `success` or `failed`, using exponential backoff.
**When to use:** CANV-04 — one job per design covers all pages; single-page export for final delivery per certificate.
**Example:**
```python
# Source: https://www.canva.dev/docs/connect/api-reference/exports/create-design-export-job/
# POST https://api.canva.com/rest/v1/exports
# Body: { "design_id": "...", "format": { "type": "pdf" } }
# Optional: "pages": [1, 3, 5]  # export specific pages only

async def poll_export(client: httpx.AsyncClient, job_id: str) -> list[str]:
    """Returns list of download URLs when export completes."""
    delay = 2.0
    for _ in range(20):  # max ~68 seconds
        await asyncio.sleep(delay)
        resp = await client.get(f"/v1/exports/{job_id}")
        job = resp.json()["job"]
        if job["status"] == "success":
            return job["urls"]
        if job["status"] == "failed":
            raise RuntimeError(f"Export job {job_id} failed")
        delay = min(delay * 1.5, 10.0)  # exponential backoff, cap at 10s
    raise TimeoutError(f"Export job {job_id} timed out")
```

### Anti-Patterns to Avoid
- **Calling validate_config() at import time:** Existing pattern prevents this — keep all config access lazy to avoid pytest import issues
- **Storing tokens in .env:** Tokens rotate; use keyring instead. Only static credentials (client_id/secret) go in .env
- **Creating one export job per certificate page:** Rate limit is 75 jobs per 5 minutes per user. For a 10-page design, exporting all pages in one job then slicing by page number avoids rate limit thrashing
- **Assuming pages endpoint returns text:** It returns only index, dimensions, thumbnail URL — never text content

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser | pdfplumber | Handles font encoding, ligatures, multi-column layout edge cases |
| PKCE code_challenge | Custom crypto | hashlib + base64 stdlib | SHA-256 + base64url is standard; easy to get wrong with padding |
| Token persistence | Write tokens to a file | keyring | keyring uses OS-native secure storage (Keychain/Secret Service) |
| HTTP retries | Manual retry loop | httpx + manual backoff (simple) | httpx doesn't auto-retry by default; simple exponential sleep is sufficient for this use case |

**Key insight:** The Canva API surface is narrow — don't build an SDK wrapper. A thin `canva_api.py` with just the 4-5 needed calls is sufficient.

## Common Pitfalls

### Pitfall 1: Pages Endpoint Returns No Text
**What goes wrong:** Developer calls `GET /v1/designs/{id}/pages` expecting page titles or text content and gets only `{index, dimensions, thumbnail}`.
**Why it happens:** The Canva Connect API intentionally limits content exposure; text elements are only accessible via the Apps SDK (browser-based).
**How to avoid:** Use the PDF export + pdfplumber strategy documented above.
**Warning signs:** If you see only `index`, `dimensions.width`, `dimensions.height`, `thumbnail.url` in the pages response — that's all you get.

### Pitfall 2: Export Rate Limits
**What goes wrong:** Creating 10+ individual export jobs (one per page) triggers the per-user rate limit of 75 jobs per 5-minute window.
**Why it happens:** Naive "one export per certificate" implementation.
**How to avoid:** Export the full design in one job first (for text extraction), then export only matched certificate pages in one batched job using the `pages` array parameter.
**Warning signs:** HTTP 429 responses from `POST /v1/exports`.

### Pitfall 3: PDF Download URLs Expire in 24 Hours
**What goes wrong:** Tool exports PDFs, stores only the download URL in `Certificate.export_url`, and Phase 3 tries to download them hours later — getting 403/404.
**Why it happens:** Canva export URLs are temporary (24-hour TTL).
**How to avoid:** Download the PDFs to a temp directory immediately after export completes. Store the local file path in `Certificate.export_url` (or add a `local_path` field).
**Warning signs:** HTTP 403 errors when downloading previously successful export URLs.

### Pitfall 4: Name Extraction Heuristic Fails on Certain Designs
**What goes wrong:** The "longest line" heuristic picks a section title or label instead of the participant name.
**Why it happens:** Certificate templates vary — some have labels like "CERTIFICAMOS QUE" that are long.
**How to avoid:** Validate against the real design during Phase 2 (success criterion 3 explicitly requires this). Consider filtering lines that match known template phrases, or use vertical position (pdfplumber provides `y0` per character) to prefer names near the vertical center of the page.
**Warning signs:** Extracted name does not match visible name on certificate.

### Pitfall 5: OAuth Redirect Port Conflicts
**What goes wrong:** Port chosen for local redirect server is already in use.
**Why it happens:** Fixed port (e.g., 3001) clashes with other running services.
**How to avoid:** Use `port=0` with Python's `http.server.HTTPServer` to get an OS-assigned free port, then register that port as the redirect URI dynamically — but note Canva requires pre-registered redirect URIs in the Developer Portal. Easiest: register `http://127.0.0.1:3001` and use that fixed port with a clear error message if it's in use.
**Warning signs:** `OSError: [Errno 48] Address already in use`.

## Code Examples

Verified patterns from official sources:

### Canva Auth Token Exchange
```python
# Source: https://www.canva.dev/docs/connect/api-reference/authentication/generate-access-token/
import base64, httpx

def _basic_auth_header(client_id: str, client_secret: str) -> str:
    return "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

async def exchange_code_for_tokens(
    code: str, code_verifier: str, redirect_uri: str,
    client_id: str, client_secret: str
) -> dict:
    async with httpx.AsyncClient(base_url="https://api.canva.com/rest/v1") as client:
        resp = await client.post(
            "/oauth/token",
            headers={"Authorization": _basic_auth_header(client_id, client_secret)},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
            },
        )
        resp.raise_for_status()
        return resp.json()
        # Returns: access_token, refresh_token, token_type, expires_in (14400), scope
```

### List Design Pages
```python
# Source: https://www.canva.dev/docs/connect/api-reference/designs/get-design-pages/
async def list_pages(client: httpx.AsyncClient, design_id: str) -> list[dict]:
    resp = await client.get(f"/v1/designs/{design_id}/pages")
    resp.raise_for_status()
    return resp.json()["items"]
    # Each item: {"index": 1, "dimensions": {...}, "thumbnail": {"url": ..., "width": ..., "height": ...}}
    # NOTE: no title or text content returned
```

### Create PDF Export Job
```python
# Source: https://www.canva.dev/docs/connect/api-reference/exports/create-design-export-job/
async def create_export_job(
    client: httpx.AsyncClient,
    design_id: str,
    pages: list[int] | None = None,
) -> str:
    body = {
        "design_id": design_id,
        "format": {"type": "pdf"},
    }
    if pages:
        body["format"]["pages"] = pages  # 1-indexed
    resp = await client.post("/v1/exports", json=body)
    resp.raise_for_status()
    return resp.json()["job"]["id"]
```

### pdfplumber Text Extraction
```python
# Source: https://github.com/jsvine/pdfplumber (confirmed installed: 0.11.9)
import pdfplumber, io

def extract_texts_from_pdf(pdf_bytes: bytes) -> list[str]:
    """One string per PDF page, empty string if no text found."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyPDF2 for PDF text | pdfplumber / pypdf | ~2022 | PyPDF2 is unmaintained; pdfplumber is the maintained standard |
| requests for HTTP | httpx | ~2020 onwards | httpx is async-capable and has cleaner API |
| Store tokens in .env | keyring | Best practice | OS-native secure storage; tokens are ephemeral and should not be committed |

**Deprecated/outdated:**
- PyPDF2: No longer maintained; superceded by pypdf and pdfplumber
- Canva Content Querying API (Apps SDK): Is GA but only runs inside Canva's browser-based app sandbox — cannot be called from a backend script

## Open Questions

1. **Name extraction heuristic accuracy**
   - What we know: pdfplumber returns text; "longest line" heuristic is a reasonable start
   - What's unclear: Whether Canva-exported PDFs preserve layout in a way that makes position-based extraction reliable; whether template has static long phrases that confuse the heuristic
   - Recommendation: Phase 2 success criterion explicitly requires empirical validation against the real design — this is a build-and-test loop, not something resolvable in research

2. **PDF export page numbering alignment**
   - What we know: Canva export `pages` parameter is 1-indexed; pdfplumber's `pdf.pages` list is 0-indexed
   - What's unclear: Whether a multi-page Canva export returns one URL (multi-page PDF) or one URL per page
   - Recommendation: From the API docs, "there is a download URL for each page in the design." Treat the export as producing one URL per exported page. Test with the real design to confirm.

3. **CANVA_DESIGN_ID config**
   - What we know: Success criteria say it comes from `.env`; `config.py` does not yet have it
   - What's unclear: Whether it should be in `_REQUIRED_VARS` (which would break existing tests) or checked lazily
   - Recommendation: Add `CANVA_DESIGN_ID` as a lazily-checked var (not in `_REQUIRED_VARS`) to avoid breaking existing test_config.py behavior.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CANV-01 | `list_pages()` returns page dicts from Canva API | unit (mock httpx) | `uv run pytest tests/test_canva_api.py::test_list_pages -x` | ❌ Wave 0 |
| CANV-02 | `find_divider_index()` correctly finds "participantes" page and skips preceding pages | unit | `uv run pytest tests/test_pages.py::test_find_divider -x` | ❌ Wave 0 |
| CANV-03 | `extract_name()` returns correct name string from pdfplumber page text | unit | `uv run pytest tests/test_exporter.py::test_extract_name -x` | ❌ Wave 0 |
| CANV-04 | `create_export_job()` + `poll_export()` produce download URL list | unit (mock httpx) | `uv run pytest tests/test_exporter.py::test_export_pipeline -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_canva_api.py` — covers CANV-01: mock httpx responses for list_pages, get_design, token exchange
- [ ] `tests/test_pages.py` — covers CANV-02: divider detection with case-insensitive contains logic
- [ ] `tests/test_exporter.py` — covers CANV-03 + CANV-04: name extraction heuristic + export job polling state machine
- [ ] `tests/conftest.py` — shared fixtures: mock httpx client, sample PDF bytes, fake token data

## Sources

### Primary (HIGH confidence)
- `https://www.canva.dev/docs/connect/api-reference/designs/get-design-pages/` — confirmed page response fields (index, dimensions, thumbnail — NO text)
- `https://www.canva.dev/docs/connect/api-reference/exports/create-design-export-job/` — PDF export params, pages array, rate limits
- `https://www.canva.dev/docs/connect/api-reference/exports/get-design-export-job/` — polling statuses, urls array structure
- `https://www.canva.dev/docs/connect/api-reference/authentication/generate-access-token/` — token endpoint URL, request format, response fields
- `https://deepwiki.com/canva-sdks/canva-connect-api-starter-kit/2.2-authentication-and-authorization` — OAuth flow steps, token TTL (14400s), refresh pattern
- PyPI registry (httpx 0.28.1, pdfplumber 0.11.9, keyring 25.7.0) — verified versions

### Secondary (MEDIUM confidence)
- `https://www.canva.dev/docs/connect/appendix/scopes/` — `design:meta:read` and `design:content:read` scopes confirmed
- `https://community.canva.dev/t/unwrapping-the-tenth-festive-release-for-2024-content-querying-api-now-in-ga/5535` — confirmed Content Querying API is Apps SDK only (not Connect API)
- `https://github.com/jsvine/pdfplumber` — pdfplumber API for `extract_text()`, `io.BytesIO` usage pattern

### Tertiary (LOW confidence)
- pdfplumber character position API for name heuristic refinement — general docs confirmed but not validated against Canva-exported PDFs specifically

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified against PyPI registry
- Architecture: MEDIUM — API endpoints confirmed via official docs; text extraction strategy is empirically unvalidated (Phase 2 success criteria require this validation)
- Pitfalls: MEDIUM — derived from API docs + known Python PDF ecosystem patterns

**Research date:** 2026-03-18
**Valid until:** 2026-06-18 (Canva API surface is stable; re-verify scopes if adding new operations)
