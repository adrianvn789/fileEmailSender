"""Certificate email sender — reads matches.csv from output/ and sends emails."""

import csv
import json
from datetime import datetime
from pathlib import Path

from canva_client import config
from canva_client.mailer import create_mailer, send_all_certificates


def load_log(log_path: Path) -> dict:
    if log_path.exists():
        return json.loads(log_path.read_text())
    return {"sent": [], "last_run": None}


def save_log(log_path: Path, log: dict) -> None:
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False))


def read_matches_csv(csv_path: Path) -> list[dict]:
    """Read matches from output CSV. Returns list of {name, email, pdf_name}."""
    matches = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            matches.append(
                {
                    "name": row["name"],
                    "email": row["email"],
                    "pdf_name": row["pdf_name"],
                }
            )
    return matches


def send_subfolder(
    subfolder_name: str,
    output_base: Path,
    input_base: Path,
    csv_filename: str = "matches.csv",
) -> None:
    """Send emails for a subfolder using its matches CSV."""
    output_dir = output_base / subfolder_name
    csv_path = output_dir / csv_filename
    pdf_dir = input_base / subfolder_name

    if not csv_path.exists():
        print(f"  No matches.csv found in {output_dir}.")
        return

    matches = read_matches_csv(csv_path)
    log_name = csv_filename.replace(".csv", "_log.json")
    log_path = output_dir / log_name
    log = load_log(log_path)
    sent_log = set(log.get("sent", []))

    to_send = [m for m in matches if m["email"] not in sent_log]
    if not to_send:
        print("  All emails already sent.")
        return

    print(f"  Sending {len(to_send)} emails...")
    mailer = create_mailer(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
    sent, errors = send_all_certificates(
        mailer, to_send, pdf_dir, config.EMAIL_SUBJECT, config.EMAIL_BODY, sent_log
    )

    log["sent"] = list(sent_log)
    log["last_run"] = datetime.now().isoformat()
    save_log(log_path, log)

    print(f"  Sent: {sent}, Errors: {len(errors)}")
    if errors:
        for e in errors:
            print(f"    {e}")


def run_pipeline(csv_filename: str = "matches.csv") -> None:
    """Scan output dir for matches CSV files and send emails."""
    input_base = Path(config.INPUT_DIR)
    output_base = Path(config.OUTPUT_DIR)

    if not output_base.exists():
        print(f"Error: output directory '{output_base}' not found.")
        return

    if not config.GMAIL_USER or not config.GMAIL_APP_PASSWORD:
        print("Error: GMAIL_USER / GMAIL_APP_PASSWORD not set in .env")
        return

    subfolders = [d for d in sorted(output_base.iterdir()) if d.is_dir()]
    if not subfolders:
        print(f"No subfolders found in {output_base}")
        return

    print(f"Found {len(subfolders)} subfolder(s) in {output_base}")
    print(f"Using: {csv_filename}")
    for subfolder in subfolders:
        print(f"\n{'='*60}")
        print(f"Sending: {subfolder.name}")
        print(f"{'='*60}")
        send_subfolder(subfolder.name, output_base, input_base, csv_filename)

    print("\nDone.")
