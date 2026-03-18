"""Tests for PDF text extraction, divider detection, and name extraction."""
import pytest
from canva_client.pages import (
    extract_texts_from_pdf,
    find_divider_index,
    extract_name,
    get_certificate_pages,
)


def test_extract_texts_from_pdf(make_pdf_fixture):
    pdf_bytes = make_pdf_fixture(["Page One", "Page Two"])
    texts = extract_texts_from_pdf(pdf_bytes)
    assert len(texts) == 2
    assert "Page One" in texts[0]
    assert "Page Two" in texts[1]


def test_find_divider_exact():
    assert find_divider_index(["Intro", "Participantes", "Alice"]) == 1


def test_find_divider_case_insensitive():
    assert find_divider_index(["Intro", "PARTICIPANTES", "Alice"]) == 1


def test_find_divider_substring():
    assert find_divider_index(["Intro", "Lista de Participantes del evento", "Alice"]) == 1


def test_find_divider_not_found():
    assert find_divider_index(["Alice", "Bob"]) == -1


def test_extract_name_single_line():
    assert extract_name("Joao Pedro Silva") == "Joao Pedro Silva"


def test_extract_name_multiline():
    text = "CERTIFICADO\nJoao Pedro Silva\nparticipou do evento"
    # Longest line heuristic: "participou do evento" is 20 chars, "Joao Pedro Silva" is 16, "CERTIFICADO" is 11
    result = extract_name(text)
    assert result == "participou do evento"


def test_extract_name_empty():
    assert extract_name("") == ""


def test_get_certificate_pages(sample_certificate_pdf):
    """PDF has 4 pages: intro, divider, Joao, Maria. Should return 2 certs."""
    certs = get_certificate_pages(sample_certificate_pdf)
    assert len(certs) == 2
    assert certs[0].page_number == 3
    assert "Joao" in certs[0].name
    assert certs[1].page_number == 4
    assert "Maria" in certs[1].name
    # export_url is empty until exporter fills it
    assert certs[0].export_url == ""
    assert certs[1].export_url == ""
