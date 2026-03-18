"""Fuzzy name matching for certificate-to-attendee pairing."""
import unicodedata
from rapidfuzz import fuzz
from canva_client.models import Certificate, Attendee, MatchResult, PipelineResult
from canva_client import config


def normalize_name(name: str) -> str:
    """NFD decompose, strip combining characters, lowercase, collapse whitespace."""
    nfd = unicodedata.normalize("NFD", name)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return " ".join(stripped.lower().split())


def match_name(
    cert_name: str, attendee_name: str, threshold: int = config.MATCH_THRESHOLD
) -> tuple[float, bool]:
    """Return (score, matched). Score is 0-100 float."""
    score = fuzz.partial_token_sort_ratio(
        normalize_name(cert_name),
        normalize_name(attendee_name),
        processor=None,
    )
    return score, score >= threshold


def match_all(
    certificates: list[Certificate],
    attendees: list[Attendee],
    threshold: int = config.MATCH_THRESHOLD,
) -> PipelineResult:
    """Greedy best-match: for each certificate, find the highest-scoring attendee."""
    result = PipelineResult()
    matched_attendees: set[int] = set()

    for cert in certificates:
        best_score = -1.0
        best_attendee = None
        best_idx = -1
        for idx, attendee in enumerate(attendees):
            if idx in matched_attendees:
                continue
            score, _ = match_name(cert.name, attendee.name, threshold)
            if score > best_score:
                best_score = score
                best_attendee = attendee
                best_idx = idx

        if best_attendee and best_score >= threshold:
            result.matches.append(
                MatchResult(cert, best_attendee, best_score, matched=True)
            )
            matched_attendees.add(best_idx)
        else:
            result.unmatched_certificates.append(cert)

    for idx, attendee in enumerate(attendees):
        if idx not in matched_attendees:
            result.unmatched_attendees.append(attendee)

    return result
