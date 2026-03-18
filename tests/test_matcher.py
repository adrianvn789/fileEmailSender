"""Tests for fuzzy name matcher."""
import pytest
from canva_client.matcher import normalize_name, match_name, match_all
from canva_client.models import Certificate, Attendee


class TestNormalizeName:
    def test_lowercase(self):
        assert normalize_name("Mariana Perez") == "mariana perez"

    def test_strip_accents(self):
        assert normalize_name("Mariana P\u00e9rez") == "mariana perez"

    def test_collapse_whitespace(self):
        assert normalize_name("  spaces   here  ") == "spaces here"

    def test_combined(self):
        assert normalize_name("  Mar\u00eda   P\u00e9rez  ") == "maria perez"


class TestMatchName:
    @pytest.mark.parametrize(
        "cert_name,attendee_name,expect_match",
        [
            ("Maria Silva", "Maria Silva", True),
            ("Maria Silva", "Silva Maria", True),
            ("Maria P\u00e9rez", "Maria Perez", True),
            ("Maria Silva", "Mariana Silva", False),
            ("Ana", "Carlos", False),
        ],
    )
    def test_match_name(self, cert_name, attendee_name, expect_match):
        _, matched = match_name(cert_name, attendee_name, threshold=90)
        assert matched == expect_match


class TestMatchAll:
    def _make_cert(self, name, page=1):
        return Certificate(page_number=page, name=name, export_url=f"https://example.com/{page}.pdf")

    def _make_att(self, name, email=None):
        return Attendee(name=name, email=email or f"{name.lower().replace(' ', '.')}@example.com")

    def test_all_matched(self):
        certs = [self._make_cert("Maria Silva", 1), self._make_cert("Jo\u00e3o Costa", 2)]
        atts = [self._make_att("Maria Silva"), self._make_att("Joao Costa")]
        result = match_all(certs, atts, threshold=90)
        assert len(result.matches) == 2
        assert len(result.unmatched_certificates) == 0
        assert len(result.unmatched_attendees) == 0

    def test_unmatched_certificate(self):
        certs = [self._make_cert("Maria Silva", 1), self._make_cert("Unknown Person", 2)]
        atts = [self._make_att("Maria Silva")]
        result = match_all(certs, atts, threshold=90)
        assert len(result.matches) == 1
        assert len(result.unmatched_certificates) == 1
        assert result.unmatched_certificates[0].name == "Unknown Person"

    def test_unmatched_attendee(self):
        certs = [self._make_cert("Maria Silva", 1)]
        atts = [self._make_att("Maria Silva"), self._make_att("Extra Person")]
        result = match_all(certs, atts, threshold=90)
        assert len(result.matches) == 1
        assert len(result.unmatched_attendees) == 1
        assert result.unmatched_attendees[0].name == "Extra Person"
