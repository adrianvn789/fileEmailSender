"""PDF export pipeline: create jobs, poll status, download files."""
import asyncio
from pathlib import Path

import httpx

from canva_client.canva_api import CanvaClient
from canva_client.models import Certificate


async def create_export_job(
    client: CanvaClient,
    design_id: str,
    pages: list[int] | None = None,
) -> str:
    """Create a PDF export job via Canva API. Returns job ID."""
    body: dict = {
        "design_id": design_id,
        "format": {"type": "pdf"},
    }
    if pages:
        body["format"]["pages"] = pages
    resp = await client.http.post("/exports", json=body)
    resp.raise_for_status()
    return resp.json()["job"]["id"]


async def poll_export(
    client: CanvaClient,
    job_id: str,
    max_attempts: int = 20,
    initial_delay: float = 2.0,
) -> list[str]:
    """Poll until export job succeeds. Returns list of download URLs."""
    delay = initial_delay
    for _ in range(max_attempts):
        await asyncio.sleep(delay)
        resp = await client.http.get(f"/exports/{job_id}")
        resp.raise_for_status()
        job = resp.json()["job"]
        if job["status"] == "success":
            return job["urls"]
        if job["status"] == "failed":
            raise RuntimeError(f"Export job {job_id} failed")
        delay = min(delay * 1.5, 10.0)
    raise TimeoutError(f"Export job {job_id} timed out after {max_attempts} attempts")


async def download_pdf(client: CanvaClient, url: str) -> bytes:
    """Download PDF bytes from a Canva export URL."""
    # Use a fresh client since the URL is absolute (not relative to base_url)
    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.get(url)
        resp.raise_for_status()
        return resp.content


async def export_full_design(
    client: CanvaClient,
    design_id: str,
) -> bytes:
    """Export the full design as a single PDF and return the bytes."""
    job_id = await create_export_job(client, design_id)
    urls = await poll_export(client, job_id)
    if not urls:
        raise RuntimeError("Export job returned no download URLs")
    return await download_pdf(client, urls[0])


async def export_certificate_pdfs(
    client: CanvaClient,
    certificates: list[Certificate],
    output_dir: Path,
    design_id: str,
) -> list[Certificate]:
    """Export each certificate page as an individual PDF and save to output_dir.

    Updates each Certificate.export_url with the local file path.
    Returns the updated list of certificates.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    updated = []

    for cert in certificates:
        job_id = await create_export_job(client, design_id, pages=[cert.page_number])
        urls = await poll_export(client, job_id)
        if not urls:
            raise RuntimeError(f"Export job for page {cert.page_number} returned no URLs")
        pdf_bytes = await download_pdf(client, urls[0])

        filename = f"certificate_page_{cert.page_number}_{cert.name.replace(' ', '_')}.pdf"
        filepath = output_dir / filename
        filepath.write_bytes(pdf_bytes)

        updated.append(Certificate(
            page_number=cert.page_number,
            name=cert.name,
            export_url=str(filepath),
        ))
    return updated
