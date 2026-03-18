"""OAuth 2.0 PKCE authentication for Canva Connect API."""
import base64
import hashlib
import json
import secrets
import time
import urllib.parse
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional
import webbrowser

import httpx
import keyring

CANVA_AUTH_URL = "https://www.canva.dev/rest/v1/oauth/authorize"
CANVA_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
KEYRING_SERVICE = "canva-client"
REDIRECT_PORT = 3001
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/callback"


def generate_pkce() -> tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge pair."""
    verifier = secrets.token_urlsafe(96)[:128]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    """Encode client credentials as HTTP Basic auth header value."""
    return "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()


def build_auth_url(client_id: str, redirect_uri: str, code_challenge: str, state: str) -> str:
    """Build the Canva OAuth authorization URL with PKCE params."""
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": "design:meta:read design:content:read",
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"{CANVA_AUTH_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_tokens(
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> dict:
    """Exchange an authorization code for access and refresh tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            CANVA_TOKEN_URL,
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


async def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict:
    """Refresh an expired access token using the stored refresh token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            CANVA_TOKEN_URL,
            headers={"Authorization": _basic_auth_header(client_id, client_secret)},
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        resp.raise_for_status()
        return resp.json()


@dataclass
class TokenStore:
    """Stores OAuth tokens with expiry tracking and keyring persistence."""

    access_token: str
    refresh_token: str
    expires_at: float  # Unix timestamp

    def is_expired(self) -> bool:
        """Return True if the access token has expired."""
        return time.time() >= self.expires_at

    def save(self) -> None:
        """Persist tokens to the OS keyring."""
        data = json.dumps({
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        })
        keyring.set_password(KEYRING_SERVICE, "tokens", data)

    @classmethod
    def load(cls) -> Optional["TokenStore"]:
        """Load tokens from the OS keyring. Returns None if no tokens stored."""
        raw = keyring.get_password(KEYRING_SERVICE, "tokens")
        if not raw:
            return None
        data = json.loads(raw)
        return cls(**data)


class _CallbackHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler to capture the OAuth callback redirect."""

    auth_code: Optional[str] = None
    state: Optional[str] = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        _CallbackHandler.auth_code = params.get("code", [None])[0]
        _CallbackHandler.state = params.get("state", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Authentication successful!</h1>"
            b"<p>You can close this tab.</p></body></html>"
        )

    def log_message(self, format, *args):
        pass  # Silence HTTP server logs


def authenticate(client_id: str, client_secret: str) -> TokenStore:
    """Run full OAuth PKCE flow: open browser, capture code, exchange for tokens."""
    import asyncio

    verifier, challenge = generate_pkce()
    state = secrets.token_urlsafe(32)
    auth_url = build_auth_url(client_id, REDIRECT_URI, challenge, state)

    _CallbackHandler.auth_code = None
    _CallbackHandler.state = None
    server = HTTPServer(("127.0.0.1", REDIRECT_PORT), _CallbackHandler)

    def run_server():
        server.handle_request()  # Handle exactly one request

    thread = Thread(target=run_server, daemon=True)
    thread.start()

    print("Opening browser for Canva authentication...")
    print(f"If browser doesn't open, visit: {auth_url}")
    webbrowser.open(auth_url)

    thread.join(timeout=120)
    server.server_close()

    if not _CallbackHandler.auth_code:
        raise RuntimeError("No authorization code received from Canva")
    if _CallbackHandler.state != state:
        raise RuntimeError("OAuth state mismatch — possible CSRF attack")

    tokens = asyncio.run(exchange_code_for_tokens(
        code=_CallbackHandler.auth_code,
        code_verifier=verifier,
        redirect_uri=REDIRECT_URI,
        client_id=client_id,
        client_secret=client_secret,
    ))

    store = TokenStore(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_at=time.time() + tokens.get("expires_in", 14400),
    )
    store.save()
    return store


async def get_access_token(client_id: str, client_secret: str) -> str:
    """Get a valid access token, refreshing if expired, authenticating if none stored."""
    store = TokenStore.load()
    if store is None:
        store = authenticate(client_id, client_secret)
        return store.access_token

    if store.is_expired():
        tokens = await refresh_access_token(store.refresh_token, client_id, client_secret)
        store = TokenStore(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_at=time.time() + tokens.get("expires_in", 14400),
        )
        store.save()

    return store.access_token
