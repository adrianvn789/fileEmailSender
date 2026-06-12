"""Match certificate PDFs to attendee names/emails from Excel files."""

import csv
import re
import unicodedata
from pathlib import Path

import openpyxl
import pdfplumber
from rapidfuzz import fuzz

from file_email_sender import config


def normalize(name: str) -> str:
    """Normalize name for fuzzy comparison: strip accents, lowercase, collapse whitespace."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    return " ".join(name.lower().split())


def read_attendees_xlsx(xlsx_path: Path) -> list[dict]:
    """Read name/email pairs from an Excel file (first two columns, no header)."""
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb.active
    attendees = []
    for row in ws.iter_rows(values_only=True):
        name, email = row[0], row[1] if len(row) > 1 else None
        if name and email:
            attendees.append({"name": str(name).strip(), "email": str(email).strip()})
    wb.close()
    return attendees


# Marker variants: "Certificado a:", "Certificado:", "Certifica a:", "Certifica:",
# optional space before the colon ("Certificado a :").
_MARKER_RE = re.compile(r"certifica(?:do)?\s*a?\s*:", re.IGNORECASE)
# No-colon variant: only "certificado a" / "certifica a" at end of line.
# A bare "certificado" ending a line is common prose and must not trigger.
_MARKER_EOL_RE = re.compile(r"certifica(?:do)?\s+a\s*$", re.IGNORECASE)


def extract_name_from_pdf(pdf_path: Path) -> str | None:
    """Extract the certificate recipient name from a PDF.

    Looks for a marker line ("Certificado a:", "Certifica a:", "Certificado:", ...)
    and returns the text after the colon on the same line, or the next line.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text()
            if not text:
                return None
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for i, line in enumerate(lines):
                m = _MARKER_RE.search(line)
                if m:
                    rest = line[m.end():].strip()
                    if rest:
                        return rest
                    return lines[i + 1] if i + 1 < len(lines) else None
                if _MARKER_EOL_RE.search(line):
                    return lines[i + 1] if i + 1 < len(lines) else None
    except Exception:
        return None
    return None


def name_from_filename(pdf_name: str) -> str:
    """Derive a candidate name from a PDF filename (fallback when extraction fails)."""
    stem = Path(pdf_name).stem
    return re.sub(r"[_\-.]+", " ", stem).strip()


def match_certificates(
    attendees: list[dict],
    pdf_dir: Path,
    threshold: int | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Match attendees to certificate PDFs using fuzzy matching.

    Returns (matches, unmatched_attendees, unmatched_pdfs).
    """
    if threshold is None:
        threshold = config.MATCH_THRESHOLD

    # Extract names from all PDFs; fall back to the filename when the
    # PDF text has no recognizable marker line.
    cert_names: dict[str, tuple[str, str]] = {}  # pdf_name -> (name, source)
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        name = extract_name_from_pdf(pdf_path)
        if name:
            cert_names[pdf_path.name] = (name, "text")
        else:
            cert_names[pdf_path.name] = (name_from_filename(pdf_path.name), "filename")

    # Greedy best-match: for each attendee, find the best matching certificate
    used_pdfs: set[str] = set()
    matches = []
    unmatched_attendees = []

    for att in attendees:
        best_score = 0
        best_pdf = None
        best_cert_name = None

        for pdf_name, (cert_name, source) in cert_names.items():
            if pdf_name in used_pdfs:
                continue
            # Filenames may contain only part of the name (plus junk like
            # "cert_"), so use token_set_ratio, which scores subsets high.
            scorer = fuzz.token_set_ratio if source == "filename" else fuzz.token_sort_ratio
            score = scorer(normalize(att["name"]), normalize(cert_name))
            if score > best_score:
                best_score = score
                best_pdf = pdf_name
                best_cert_name = cert_name

        if best_score >= threshold and best_pdf:
            matches.append(
                {
                    "name": att["name"],
                    "email": att["email"],
                    "matched_name": best_cert_name,
                    "pdf_name": best_pdf,
                    "score": best_score,
                }
            )
            used_pdfs.add(best_pdf)
        else:
            unmatched_attendees.append(att)

    unmatched_pdfs = [p for p in cert_names if p not in used_pdfs]
    return matches, unmatched_attendees, unmatched_pdfs


def run_matching(
    attendee_folder: str,
    certificate_folder: str | None = None,
) -> None:
    """Run the matching pipeline for a given attendee folder.

    If certificate_folder is not provided, uses the same folder as attendee_folder.
    """
    input_base = Path(config.INPUT_DIR)
    output_base = Path(config.OUTPUT_DIR)

    attendee_dir = input_base / attendee_folder
    cert_dir = input_base / (certificate_folder or attendee_folder)

    # Find the Excel file
    xlsx_files = list(attendee_dir.glob("*.xlsx"))
    xlsx_files = [f for f in xlsx_files if not f.name.startswith("~$")]
    if not xlsx_files:
        print(f"Error: no .xlsx file found in {attendee_dir}")
        return
    xlsx_path = xlsx_files[0]

    # Read attendees
    attendees = read_attendees_xlsx(xlsx_path)
    print(f"Loaded {len(attendees)} attendees from {xlsx_path.name}")

    # Find PDFs
    pdf_count = len(list(cert_dir.glob("*.pdf")))
    print(f"Found {pdf_count} PDFs in {cert_dir.name}")

    # Match
    matches, unmatched_att, unmatched_pdfs = match_certificates(attendees, cert_dir)
    print(f"\nResults:")
    print(f"  Matched:              {len(matches)}")
    print(f"  Unmatched attendees:  {len(unmatched_att)}")
    print(f"  Unmatched PDFs:       {len(unmatched_pdfs)}")

    # Write output
    output_dir = output_base / attendee_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "matches.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "email", "matched_name", "pdf_name", "score"])
        writer.writeheader()
        writer.writerows(matches)
    print(f"\nWrote {csv_path}")

    if matches:
        print("\nMatches:")
        for m in matches:
            print(f"  {m['name']} -> {m['matched_name']} ({m['score']:.0f}%) [{m['pdf_name']}]")

    if unmatched_att:
        print("\nUnmatched attendees:")
        for u in unmatched_att:
            print(f"  {u['name']} <{u['email']}>")

    if unmatched_pdfs:
        print("\nUnmatched PDFs:")
        for p in unmatched_pdfs:
            print(f"  {p}")
