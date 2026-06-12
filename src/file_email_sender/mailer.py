"""Email sender for certificate delivery via Gmail."""
import time
from pathlib import Path

import yagmail


def create_mailer(gmail_user: str, gmail_app_password: str) -> yagmail.SMTP:
    return yagmail.SMTP(user=gmail_user, password=gmail_app_password)


def send_all_certificates(
    mailer: yagmail.SMTP,
    matches: list[dict],
    pdf_dir: Path,
    subject: str,
    body_template: str,
    sent_log: set[str],
    delay: float = 1.5,
) -> tuple[int, list[str]]:
    """Send certificates to all matches. Returns (sent_count, errors)."""
    sent = 0
    errors = []

    for m in matches:
        if m["email"] in sent_log:
            print(f"  SKIP (already sent): {m['name']}")
            continue

        try:
            pdf_path = pdf_dir / m["pdf_name"]
            body = body_template.format(nombre=m["name"])
            mailer.send(
                to=m["email"],
                subject=subject,
                contents=body,
                attachments=[str(pdf_path)],
            )
            sent += 1
            sent_log.add(m["email"])
            print(f"  SENT: {m['name']} <{m['email']}>")
            time.sleep(delay)
        except Exception as e:
            errors.append(f"{m['name']} <{m['email']}>: {e}")
            print(f"  FAIL: {m['name']} <{m['email']}> — {e}")

    return sent, errors
