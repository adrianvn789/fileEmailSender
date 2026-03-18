---
phase: 02-canva-integration
plan: 01
subsystem: canva-auth
tags: [oauth, pkce, httpx, keyring, async]
dependency_graph:
  requires: []
  provides: [canva-auth, canva-api-client]
  affects: [02-02, 02-03, 02-04]
tech_stack:
  added: [httpx==0.28.1, keyring==25.7.0, pytest-asyncio==1.3.0]
  patterns: [oauth-pkce, async-context-manager, keyring-token-store]
key_files:
  created:
    - src/canva_client/auth.py
    - src/canva_client/canva_api.py
    - tests/conftest.py
    - tests/test_canva_api.py
  modified:
    - src/canva_client/config.py
    - pyproject.toml
    - .env.example
    - uv.lock
decisions:
  - "pytest-asyncio asyncio_mode=auto chosen over manual asyncio.run() in tests for cleaner async test syntax"
  - "CANVA_DESIGN_ID kept out of _REQUIRED_VARS to avoid breaking existing test_config.py behavior (lazy access pattern)"
  - "TokenStore uses keyring for OS-native secure storage rather than plaintext .env"
metrics:
  duration_seconds: 152
  completed_date: "2026-03-18"
  tasks_completed: 1
  tasks_total: 1
  files_created: 4
  files_modified: 4
---

# Phase 2 Plan 1: Canva OAuth PKCE Auth and API Client Summary

**One-liner:** OAuth 2.0 PKCE browser flow with keyring token persistence, auto-refresh, and async httpx-based Canva API client supporting list_pages().

## What Was Built

- `src/canva_client/auth.py` — Full OAuth PKCE implementation: PKCE pair generation (SHA-256/base64url), authorization URL builder, code exchange and token refresh via httpx, `TokenStore` dataclass with keyring persistence and expiry checking, `authenticate()` browser flow (local HTTP callback server on port 3001), `get_access_token()` orchestrator that refreshes or re-authenticates as needed.

- `src/canva_client/canva_api.py` — Thin async API client: `CanvaClient` wraps `httpx.AsyncClient` with the Canva base URL and Bearer auth header, `list_pages(client, design_id)` hits `GET /designs/{id}/pages` and returns the items array.

- `tests/conftest.py` — Shared fixtures: `sample_pages_response` (3-page response), `sample_token_response` (fake access/refresh tokens).

- `tests/test_canva_api.py` — 8 unit tests covering PKCE generation correctness, auth URL construction, token exchange, token refresh, TokenStore save/load via mocked keyring, TokenStore expiry logic, list_pages return shape, CanvaClient auth header.

## Decisions Made

1. **pytest-asyncio asyncio_mode=auto** — Avoids `@pytest.mark.asyncio` decorator noise on every async test function. Cleaner and consistent with project style.

2. **CANVA_DESIGN_ID outside `_REQUIRED_VARS`** — Adding it to `_REQUIRED_VARS` would cause `test_config.py`'s empty-env subprocess test to name `CANVA_DESIGN_ID` instead of `CANVA_CLIENT_ID`, breaking an existing test. Lazy access preserves the existing test behavior.

3. **TokenStore via keyring** — Tokens are ephemeral (4-hour TTL) and must rotate; storing them in `.env` or plaintext files would create stale/invalid credentials across runs. Keyring uses macOS Keychain / Linux Secret Service.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing pytest-asyncio plugin**
- **Found during:** Task 1, GREEN phase (running async tests)
- **Issue:** Tests using `@pytest.mark.asyncio` failed with "async def functions are not natively supported" because pytest-asyncio was not installed
- **Fix:** Ran `uv add --dev "pytest-asyncio>=0.24.0"` and added `asyncio_mode = "auto"` to `[tool.pytest.ini_options]` in pyproject.toml
- **Files modified:** pyproject.toml, uv.lock
- **Commit:** c8d81a0 (included in the same task commit)

## Test Results

```
26 passed in 1.41s
```

All 8 new tests pass. All 18 pre-existing tests continue to pass.

## Self-Check: PASSED

- `src/canva_client/auth.py` — FOUND
- `src/canva_client/canva_api.py` — FOUND
- `tests/conftest.py` — FOUND
- `tests/test_canva_api.py` — FOUND
- Commit `c8d81a0` — FOUND
