"""Tests for Canva OAuth PKCE auth module and API client."""
import base64
import hashlib
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from canva_client.auth import (
    TokenStore,
    build_auth_url,
    exchange_code_for_tokens,
    generate_pkce,
    refresh_access_token,
)
from canva_client.canva_api import CanvaClient, list_pages


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def test_generate_pkce():
    """generate_pkce() returns (verifier, challenge) with correct properties."""
    verifier, challenge = generate_pkce()

    # verifier must be 43-128 URL-safe chars
    assert 43 <= len(verifier) <= 128
    # All chars must be URL-safe (base64url alphabet)
    import re
    assert re.fullmatch(r"[A-Za-z0-9_\-]+", verifier)

    # challenge must equal base64url(sha256(verifier)) without padding
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    assert challenge == expected


def test_build_auth_url():
    """build_auth_url() returns URL with all required OAuth params."""
    url = build_auth_url(
        client_id="test_client",
        redirect_uri="http://127.0.0.1:3001/callback",
        code_challenge="abc_challenge",
        state="xyz_state",
    )

    assert url.startswith("https://www.canva.dev/rest/v1/oauth/authorize")
    assert "client_id=test_client" in url
    assert "redirect_uri=" in url
    assert "code_challenge=abc_challenge" in url
    assert "state=xyz_state" in url
    assert "code_challenge_method=S256" in url


# ---------------------------------------------------------------------------
# Token exchange and refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exchange_code(sample_token_response):
    """exchange_code_for_tokens() POSTs and returns token dict."""
    mock_response = MagicMock()
    mock_response.json.return_value = sample_token_response
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await exchange_code_for_tokens(
            code="auth_code",
            code_verifier="verifier",
            redirect_uri="http://127.0.0.1:3001/callback",
            client_id="cid",
            client_secret="csec",
        )

    assert "access_token" in result
    assert result["access_token"] == "fake_access_token_12345"
    assert "refresh_token" in result


@pytest.mark.asyncio
async def test_refresh_tokens(sample_token_response):
    """refresh_access_token() POSTs with refresh_token grant and returns new token dict."""
    new_token_response = {**sample_token_response, "access_token": "new_access_token_99"}
    mock_response = MagicMock()
    mock_response.json.return_value = new_token_response
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await refresh_access_token(
            refresh_token="rt",
            client_id="cid",
            client_secret="csec",
        )

    assert "access_token" in result
    assert result["access_token"] == "new_access_token_99"


# ---------------------------------------------------------------------------
# TokenStore
# ---------------------------------------------------------------------------

def test_token_store_save_load():
    """TokenStore.save() writes to keyring, TokenStore.load() reads back same tokens."""
    stored = {}

    def fake_set(service, key, value):
        stored[(service, key)] = value

    def fake_get(service, key):
        return stored.get((service, key))

    with patch("keyring.set_password", side_effect=fake_set), \
         patch("keyring.get_password", side_effect=fake_get):
        original = TokenStore(
            access_token="acc_tok",
            refresh_token="ref_tok",
            expires_at=9999999999.0,
        )
        original.save()
        loaded = TokenStore.load()

    assert loaded is not None
    assert loaded.access_token == "acc_tok"
    assert loaded.refresh_token == "ref_tok"
    assert loaded.expires_at == 9999999999.0


def test_token_store_is_expired():
    """TokenStore.is_expired() returns True when expires_at is in the past."""
    past_store = TokenStore(
        access_token="a",
        refresh_token="r",
        expires_at=time.time() - 100,  # already expired
    )
    assert past_store.is_expired() is True

    future_store = TokenStore(
        access_token="a",
        refresh_token="r",
        expires_at=time.time() + 3600,  # expires in an hour
    )
    assert future_store.is_expired() is False


# ---------------------------------------------------------------------------
# CanvaClient and list_pages
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_pages(sample_pages_response):
    """list_pages() returns a list of page dicts with index, dimensions, thumbnail."""
    mock_response = MagicMock()
    mock_response.json.return_value = sample_pages_response
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=mock_response)

    client = CanvaClient.__new__(CanvaClient)
    client._client = mock_http

    pages = await list_pages(client, "design123")

    assert len(pages) == 3
    first = pages[0]
    assert "index" in first
    assert "dimensions" in first
    assert "thumbnail" in first


@pytest.mark.asyncio
async def test_list_pages_auth_header():
    """list_pages() sends Authorization: Bearer <token> header via CanvaClient."""
    import httpx

    access_token = "fake_access_token_12345"

    # Track calls to httpx.AsyncClient constructor
    captured_headers = {}

    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        captured_headers.update(kwargs.get("headers", {}))
        original_init(self, *args, **kwargs)

    mock_response = MagicMock()
    mock_response.json.return_value = {"items": []}
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=mock_response)

    client = CanvaClient.__new__(CanvaClient)
    client._client = mock_http

    # Verify CanvaClient is constructed with the right header
    with patch.object(httpx, "AsyncClient") as MockAsyncClient:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        MockAsyncClient.return_value = mock_instance

        real_client = CanvaClient(access_token=access_token)
        _, call_kwargs = MockAsyncClient.call_args
        headers = call_kwargs.get("headers", {})
        assert headers.get("Authorization") == f"Bearer {access_token}"
