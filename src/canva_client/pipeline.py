"""End-to-end Canva certificate extraction pipeline."""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

from canva_client import config
from canva_client.auth import get_access_token
from canva_client.canva_api import CanvaClient, list_pages
from canva_client.exporter import export_full_design, export_certificate_pdfs
from canva_client.pages import get_certificate_pages
from canva_client.models import Certificate


async def _run_pipeline(design_id: str) -> list[Certificate]:
    """Internal async pipeline implementation."""
    client_id = os.environ.get("CANVA_CLIENT_ID", "")
    client_secret = os.environ.get("CANVA_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("Error: CANVA_CLIENT_ID and CANVA_CLIENT_SECRET must be set in .env", file=sys.stderr)
        sys.exit(2)

    if not design_id:
        print("Error: CANVA_DESIGN_ID must be set in .env", file=sys.stderr)
        sys.exit(2)

    # Step 1: Authenticate
    print("Authenticating with Canva...")
    access_token = await get_access_token(client_id, client_secret)
    print("Authenticated successfully.")

    async with CanvaClient(access_token) as client:
        # Step 2: List pages (for informational output)
        print(f"\nListing pages for design {design_id}...")
        pages = await list_pages(client, design_id)
        print(f"Found {len(pages)} pages in design.")
        for p in pages:
            print(f"  Page {p['index']}: {p['dimensions']['width']}x{p['dimensions']['height']}")

        # Step 3: Export full design as PDF for text extraction
        print("\nExporting full design as PDF for text extraction...")
        pdf_bytes = await export_full_design(client, design_id)
        print(f"Downloaded PDF ({len(pdf_bytes)} bytes).")

        # Step 4: Extract certificate pages
        print("\nAnalyzing pages...")
        certificates = get_certificate_pages(pdf_bytes)

        if not certificates:
            print("No certificate pages found after Participantes divider.", file=sys.stderr)
            sys.exit(1)

        print(f"Found {len(certificates)} certificate pages after divider:")
        for cert in certificates:
            print(f"  Page {cert.page_number}: {cert.name}")

        # Step 5: Export individual certificate PDFs
        output_dir = Path(tempfile.mkdtemp(prefix="canva_certs_"))
        print(f"\nExporting individual certificate PDFs to {output_dir}...")
        certificates = await export_certificate_pdfs(client, certificates, output_dir, design_id)

        print(f"\nExport complete! {len(certificates)} PDFs saved:")
        for cert in certificates:
            print(f"  {cert.name} -> {cert.export_url}")

        return certificates


def run_canva_pipeline() -> list[Certificate]:
    """Run the full Canva pipeline synchronously."""
    design_id = config.CANVA_DESIGN_ID
    return asyncio.run(_run_pipeline(design_id))
