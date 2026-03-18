"""Tests for the PDF export pipeline: create jobs, poll, download, per-cert export."""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from canva_client.canva_api import CanvaClient
from canva_client.exporter import (
    create_export_job,
    download_pdf,
    export_certificate_pdfs,
    poll_export,
)
from canva_client.models import Certificate


def _make_client() -> CanvaClient:
    """Create a CanvaClient with a fake token (no real HTTP)."""
    return CanvaClient(access_token="fake_token")


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.content = b"PDF bytes"
    resp.raise_for_status = MagicMock()
    return resp


async def test_create_export_job():
    client = _make_client()
    mock_resp = _mock_response({"job": {"id": "job123", "status": "in_progress"}})
    client.http.post = AsyncMock(return_value=mock_resp)

    job_id = await create_export_job(client, "design123")

    assert job_id == "job123"
    call_kwargs = client.http.post.call_args
    assert "/exports" in str(call_kwargs)
    body = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
    assert body["design_id"] == "design123"
    assert body["format"]["type"] == "pdf"


async def test_create_export_job_with_pages():
    client = _make_client()
    mock_resp = _mock_response({"job": {"id": "job456", "status": "in_progress"}})
    client.http.post = AsyncMock(return_value=mock_resp)

    job_id = await create_export_job(client, "design123", pages=[3, 4])

    assert job_id == "job456"
    call_kwargs = client.http.post.call_args
    body = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
    assert body["format"]["pages"] == [3, 4]


async def test_poll_export_success():
    client = _make_client()
    in_progress = _mock_response({
        "job": {"id": "job123", "status": "in_progress"}
    })
    success = _mock_response({
        "job": {
            "id": "job123",
            "status": "success",
            "urls": ["https://export.canva.com/a.pdf"],
        }
    })
    client.http.get = AsyncMock(side_effect=[in_progress, success])

    with patch("canva_client.exporter.asyncio.sleep", new_callable=AsyncMock):
        urls = await poll_export(client, "job123")

    assert urls == ["https://export.canva.com/a.pdf"]


async def test_poll_export_failed():
    client = _make_client()
    failed = _mock_response({
        "job": {"id": "job123", "status": "failed"}
    })
    client.http.get = AsyncMock(return_value=failed)

    with patch("canva_client.exporter.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="failed"):
            await poll_export(client, "job123")


async def test_download_pdf():
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.content = b"PDF bytes"
    mock_resp.raise_for_status = MagicMock()

    with patch("canva_client.exporter.httpx.AsyncClient") as mock_async_client_cls:
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_async_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_async_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await download_pdf(client, "https://export.canva.com/a.pdf")

    assert result == b"PDF bytes"


async def test_export_certificate_pdfs(tmp_path):
    """Integration test: mocks full flow and checks files are written and export_url updated."""
    client = _make_client()
    certificates = [
        Certificate(page_number=3, name="Joao Pedro Silva", export_url=""),
        Certificate(page_number=4, name="Maria Clara Santos", export_url=""),
    ]

    job_id_counter = iter(["job_p3", "job_p4"])
    poll_urls = {
        "job_p3": ["https://export.canva.com/p3.pdf"],
        "job_p4": ["https://export.canva.com/p4.pdf"],
    }
    pdf_content = {
        "https://export.canva.com/p3.pdf": b"PDF for Joao",
        "https://export.canva.com/p4.pdf": b"PDF for Maria",
    }

    async def fake_create_export_job(c, design_id, pages=None):
        return next(job_id_counter)

    async def fake_poll_export(c, job_id, **kwargs):
        return poll_urls[job_id]

    async def fake_download_pdf(c, url):
        return pdf_content[url]

    with (
        patch("canva_client.exporter.create_export_job", side_effect=fake_create_export_job),
        patch("canva_client.exporter.poll_export", side_effect=fake_poll_export),
        patch("canva_client.exporter.download_pdf", side_effect=fake_download_pdf),
    ):
        updated = await export_certificate_pdfs(client, certificates, tmp_path, "design123")

    assert len(updated) == 2
    for cert in updated:
        path = Path(cert.export_url)
        assert path.exists(), f"Expected file at {path}"
        assert path.is_relative_to(tmp_path)

    assert updated[0].name == "Joao Pedro Silva"
    assert Path(updated[0].export_url).read_bytes() == b"PDF for Joao"
    assert updated[1].name == "Maria Clara Santos"
    assert Path(updated[1].export_url).read_bytes() == b"PDF for Maria"
