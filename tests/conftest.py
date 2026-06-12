"""Shared fixtures for certificate pipeline tests."""
import pytest
from fpdf import FPDF


def make_pdf(page_texts: list[str]) -> bytes:
    """Create a minimal PDF with one page per text string (newlines supported)."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    for text in page_texts:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 10, text)
    return bytes(pdf.output())


@pytest.fixture
def make_pdf_fixture():
    """Return the make_pdf helper function as a fixture."""
    return make_pdf
