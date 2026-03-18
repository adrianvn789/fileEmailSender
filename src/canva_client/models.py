"""Core data models for the certificate pipeline."""
from dataclasses import dataclass, field


@dataclass
class Certificate:
    page_number: int
    name: str
    export_url: str


@dataclass
class Attendee:
    name: str
    email: str


@dataclass
class MatchResult:
    certificate: Certificate
    attendee: Attendee
    score: float
    matched: bool


@dataclass
class PipelineResult:
    matches: list[MatchResult] = field(default_factory=list)
    unmatched_attendees: list[Attendee] = field(default_factory=list)
    unmatched_certificates: list[Certificate] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
