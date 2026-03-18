"""Tests for core data models."""
from canva_client.models import Certificate, Attendee, MatchResult, PipelineResult


def test_certificate_instantiation():
    cert = Certificate(page_number=1, name="Maria Silva", export_url="https://example.com/cert.pdf")
    assert cert.page_number == 1
    assert cert.name == "Maria Silva"
    assert cert.export_url == "https://example.com/cert.pdf"


def test_attendee_instantiation():
    att = Attendee(name="Maria Silva", email="maria@example.com")
    assert att.name == "Maria Silva"
    assert att.email == "maria@example.com"


def test_match_result_instantiation():
    cert = Certificate(page_number=1, name="Maria Silva", export_url="https://example.com/cert.pdf")
    att = Attendee(name="Maria Silva", email="maria@example.com")
    mr = MatchResult(certificate=cert, attendee=att, score=95.0, matched=True)
    assert mr.score == 95.0
    assert mr.matched is True


def test_pipeline_result_defaults():
    pr = PipelineResult()
    assert pr.matches == []
    assert pr.unmatched_attendees == []
    assert pr.unmatched_certificates == []
    assert pr.errors == []
