"""Shared fixtures for Canva API tests."""
import io
import pytest
from fpdf import FPDF


def make_pdf(page_texts: list[str]) -> bytes:
    """Create a minimal PDF with one page per text string."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    for text in page_texts:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, text)
    return bytes(pdf.output())


@pytest.fixture
def make_pdf_fixture():
    """Return the make_pdf helper function as a fixture."""
    return make_pdf


@pytest.fixture
def sample_certificate_pdf():
    return make_pdf([
        "Apresentacao do Evento",
        "Participantes",
        "Joao Pedro Silva",
        "Maria Clara Santos",
    ])


SAMPLE_EXPORT_JOB_RESPONSE = {
    "job": {
        "id": "export_job_123",
        "status": "in_progress",
    }
}

SAMPLE_EXPORT_COMPLETE_RESPONSE = {
    "job": {
        "id": "export_job_123",
        "status": "success",
        "urls": ["https://export.canva.com/pdf/design123.pdf"],
    }
}


@pytest.fixture
def sample_export_job_response():
    return SAMPLE_EXPORT_JOB_RESPONSE


@pytest.fixture
def sample_export_complete_response():
    return SAMPLE_EXPORT_COMPLETE_RESPONSE


SAMPLE_PAGES_RESPONSE = {
    "items": [
        {"index": 1, "dimensions": {"width": 1920, "height": 1080}, "thumbnail": {"url": "https://example.com/thumb1.png", "width": 160, "height": 90}},
        {"index": 2, "dimensions": {"width": 1920, "height": 1080}, "thumbnail": {"url": "https://example.com/thumb2.png", "width": 160, "height": 90}},
        {"index": 3, "dimensions": {"width": 1920, "height": 1080}, "thumbnail": {"url": "https://example.com/thumb3.png", "width": 160, "height": 90}},
    ]
}

SAMPLE_TOKEN_RESPONSE = {
    "access_token": "fake_access_token_12345",
    "refresh_token": "fake_refresh_token_67890",
    "token_type": "Bearer",
    "expires_in": 14400,
    "scope": "design:meta:read design:content:read",
}


@pytest.fixture
def sample_pages_response():
    return SAMPLE_PAGES_RESPONSE


@pytest.fixture
def sample_token_response():
    return SAMPLE_TOKEN_RESPONSE
