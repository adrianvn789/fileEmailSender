"""Canva Connect API client."""
import httpx

CANVA_BASE_URL = "https://api.canva.com/rest/v1"


class CanvaClient:
    """Async HTTP client for the Canva Connect API."""

    def __init__(self, access_token: str):
        self._client = httpx.AsyncClient(
            base_url=CANVA_BASE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    @property
    def http(self) -> httpx.AsyncClient:
        """Expose the underlying httpx client for direct use."""
        return self._client


async def list_pages(client: CanvaClient, design_id: str) -> list[dict]:
    """Return a list of page metadata dicts for the given Canva design ID.

    Each dict contains: index, dimensions (width/height), thumbnail (url/width/height).
    """
    resp = await client.http.get(f"/designs/{design_id}/pages")
    resp.raise_for_status()
    return resp.json()["items"]
