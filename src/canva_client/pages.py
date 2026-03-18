"""Page processing: text extraction, divider detection, name extraction."""
import io

import pdfplumber

from canva_client.models import Certificate


def extract_texts_from_pdf(pdf_bytes: bytes) -> list[str]:
    """One string per PDF page. Empty string if no text found."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def find_divider_index(page_texts: list[str]) -> int:
    """Return the 0-based index of the Participantes divider page, or -1."""
    for i, text in enumerate(page_texts):
        if "participantes" in text.lower():
            return i
    return -1


def extract_name(text: str) -> str:
    """Heuristic: return the longest non-empty line as the participant name."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return max(lines, key=len)


def get_certificate_pages(pdf_bytes: bytes) -> list[Certificate]:
    """Extract Certificate objects from pages after the Participantes divider.

    Returns Certificate objects with:
    - page_number: 1-indexed (matches Canva page numbering)
    - name: extracted participant name
    - export_url: empty string (populated later by exporter)
    """
    page_texts = extract_texts_from_pdf(pdf_bytes)
    divider_idx = find_divider_index(page_texts)
    if divider_idx == -1:
        return []  # No divider found — no certificates

    certificates = []
    for i in range(divider_idx + 1, len(page_texts)):
        name = extract_name(page_texts[i])
        if name:
            certificates.append(Certificate(
                page_number=i + 1,  # Convert 0-based to 1-indexed for Canva
                name=name,
                export_url="",
            ))
    return certificates
