"""Tests for fuzzy name matcher and PDF name extraction."""
import pytest

from file_email_sender.matcher import (
    extract_name_from_pdf,
    match_certificates,
    name_from_filename,
    normalize,
)


class TestNormalize:
    def test_lowercase(self):
        assert normalize("Mariana Perez") == "mariana perez"

    def test_strip_accents(self):
        assert normalize("Mariana Pérez") == "mariana perez"

    def test_collapse_whitespace(self):
        assert normalize("  spaces   here  ") == "spaces here"

    def test_combined(self):
        assert normalize("  María   Pérez  ") == "maria perez"


class TestExtractNameFromPdf:
    @pytest.mark.parametrize(
        "page_text,expected",
        [
            ("Certificado a:\nMaria Perez", "Maria Perez"),
            ("CERTIFICADO A:\nMaria Perez", "Maria Perez"),
            ("Certificado:\nMaria Perez", "Maria Perez"),
            ("Certifica a:\nMaria Perez", "Maria Perez"),
            ("Certifica:\nMaria Perez", "Maria Perez"),
            ("Certificado a :\nMaria Perez", "Maria Perez"),
            ("Certificado a\nMaria Perez", "Maria Perez"),
            ("Certificado a: Maria Perez", "Maria Perez"),
            ("Se otorga el presente certificado a:\nMaria Perez", "Maria Perez"),
            ("Diploma de honor\nMaria Perez", None),
        ],
    )
    def test_marker_variants(self, tmp_path, make_pdf_fixture, page_text, expected):
        pdf_path = tmp_path / "cert.pdf"
        pdf_path.write_bytes(make_pdf_fixture([page_text]))
        assert extract_name_from_pdf(pdf_path) == expected

    def test_bare_certificado_mid_prose_does_not_trigger(self, tmp_path, make_pdf_fixture):
        pdf_path = tmp_path / "cert.pdf"
        pdf_path.write_bytes(
            make_pdf_fixture(["Se entrega este certificado\npor su participacion"])
        )
        assert extract_name_from_pdf(pdf_path) is None

    def test_marker_on_last_line_returns_none(self, tmp_path, make_pdf_fixture):
        pdf_path = tmp_path / "cert.pdf"
        pdf_path.write_bytes(make_pdf_fixture(["Certificado a:"]))
        assert extract_name_from_pdf(pdf_path) is None

    def test_unreadable_pdf_returns_none(self, tmp_path):
        pdf_path = tmp_path / "broken.pdf"
        pdf_path.write_bytes(b"not a pdf")
        assert extract_name_from_pdf(pdf_path) is None


class TestNameFromFilename:
    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("maria_perez.pdf", "maria perez"),
            ("Maria-Perez.pdf", "Maria Perez"),
            ("cert_maria.perez.pdf", "cert maria perez"),
            ("Maria Perez.pdf", "Maria Perez"),
            ("MariaPerez.pdf", "Maria Perez"),
            ("certMariaPérez.pdf", "cert Maria Pérez"),
        ],
    )
    def test_separators(self, filename, expected):
        assert name_from_filename(filename) == expected


def _write_cert(tmp_path, make_pdf, filename, page_text):
    (tmp_path / filename).write_bytes(make_pdf([page_text]))


class TestMatchCertificates:
    def test_all_matched(self, tmp_path, make_pdf_fixture):
        _write_cert(tmp_path, make_pdf_fixture, "c1.pdf", "Certificado a:\nMaria Silva")
        _write_cert(tmp_path, make_pdf_fixture, "c2.pdf", "Certificado a:\nJoao Costa")
        attendees = [
            {"name": "Maria Silva", "email": "maria@example.com"},
            {"name": "João Costa", "email": "joao@example.com"},
        ]
        matches, unmatched_att, unmatched_pdfs = match_certificates(
            attendees, tmp_path, threshold=90
        )
        assert len(matches) == 2
        assert unmatched_att == []
        assert unmatched_pdfs == []

    def test_word_order_and_case(self, tmp_path, make_pdf_fixture):
        _write_cert(tmp_path, make_pdf_fixture, "c1.pdf", "Certificado a:\nSILVA MARIA")
        attendees = [{"name": "Maria Silva", "email": "maria@example.com"}]
        matches, _, _ = match_certificates(attendees, tmp_path, threshold=90)
        assert len(matches) == 1
        assert matches[0]["pdf_name"] == "c1.pdf"

    def test_unmatched_attendee(self, tmp_path, make_pdf_fixture):
        _write_cert(tmp_path, make_pdf_fixture, "c1.pdf", "Certificado a:\nMaria Silva")
        attendees = [
            {"name": "Maria Silva", "email": "maria@example.com"},
            {"name": "Extra Person", "email": "extra@example.com"},
        ]
        matches, unmatched_att, _ = match_certificates(attendees, tmp_path, threshold=90)
        assert len(matches) == 1
        assert len(unmatched_att) == 1
        assert unmatched_att[0]["name"] == "Extra Person"

    def test_unmatched_pdf(self, tmp_path, make_pdf_fixture):
        _write_cert(tmp_path, make_pdf_fixture, "c1.pdf", "Certificado a:\nMaria Silva")
        _write_cert(tmp_path, make_pdf_fixture, "c2.pdf", "Certificado a:\nUnknown Person")
        attendees = [{"name": "Maria Silva", "email": "maria@example.com"}]
        matches, _, unmatched_pdfs = match_certificates(attendees, tmp_path, threshold=90)
        assert len(matches) == 1
        assert unmatched_pdfs == ["c2.pdf"]

    def test_filename_fallback_when_no_marker(self, tmp_path, make_pdf_fixture):
        _write_cert(tmp_path, make_pdf_fixture, "maria_silva.pdf", "Diploma de honor")
        attendees = [{"name": "Maria Silva", "email": "maria@example.com"}]
        matches, unmatched_att, unmatched_pdfs = match_certificates(
            attendees, tmp_path, threshold=90
        )
        assert len(matches) == 1
        assert matches[0]["pdf_name"] == "maria_silva.pdf"
        assert unmatched_att == []
        assert unmatched_pdfs == []

    def test_filename_fallback_partial_name_with_junk(self, tmp_path, make_pdf_fixture):
        _write_cert(tmp_path, make_pdf_fixture, "cert_maria_silva.pdf", "Diploma de honor")
        attendees = [{"name": "Maria Silva", "email": "maria@example.com"}]
        matches, _, _ = match_certificates(attendees, tmp_path, threshold=90)
        assert len(matches) == 1
        assert matches[0]["pdf_name"] == "cert_maria_silva.pdf"

    def test_by_filename_ignores_pdf_text(self, tmp_path, make_pdf_fixture):
        # PDF text names the WRONG person; filename names the right one.
        _write_cert(
            tmp_path, make_pdf_fixture, "maria_silva.pdf", "Certificado a:\nJoao Costa"
        )
        attendees = [{"name": "Maria Silva", "email": "maria@example.com"}]
        matches, _, _ = match_certificates(
            attendees, tmp_path, threshold=90, by_filename=True
        )
        assert len(matches) == 1
        assert matches[0]["pdf_name"] == "maria_silva.pdf"

    def test_by_filename_fuzzy_not_exact(self, tmp_path, make_pdf_fixture):
        # Accents, case, camelCase, junk prefix, typo-free partials all match.
        _write_cert(tmp_path, make_pdf_fixture, "cert-MARIA_pérez.pdf", "x")
        _write_cert(tmp_path, make_pdf_fixture, "JoaoCosta-2024.pdf", "x")
        attendees = [
            {"name": "María Perez", "email": "maria@example.com"},
            {"name": "João Costa", "email": "joao@example.com"},
        ]
        matches, unmatched_att, unmatched_pdfs = match_certificates(
            attendees, tmp_path, threshold=90, by_filename=True
        )
        assert len(matches) == 2
        assert unmatched_att == []
        assert unmatched_pdfs == []

    def test_pdf_used_once(self, tmp_path, make_pdf_fixture):
        _write_cert(tmp_path, make_pdf_fixture, "c1.pdf", "Certificado a:\nMaria Silva")
        attendees = [
            {"name": "Maria Silva", "email": "maria@example.com"},
            {"name": "Maria Silva", "email": "maria2@example.com"},
        ]
        matches, unmatched_att, _ = match_certificates(attendees, tmp_path, threshold=90)
        assert len(matches) == 1
        assert len(unmatched_att) == 1
