"""Configuration loading and validation."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

_REQUIRED_VARS = [
    "CANVA_CLIENT_ID",
    "CANVA_CLIENT_SECRET",
    "GOOGLE_SHEET_ID",
    "GOOGLE_CREDENTIALS_PATH",
    "SMTP_USER",
    "SMTP_PASSWORD",
]


def validate_config() -> None:
    """Validate all required env vars are set. Exits 2 with message on missing var."""
    for var in _REQUIRED_VARS:
        if not os.environ.get(var):
            print(f"Error: required environment variable '{var}' is not set.", file=sys.stderr)
            sys.exit(2)


MATCH_THRESHOLD: int = int(os.environ.get("MATCH_THRESHOLD", "90"))
NAME_COLUMN: int = int(os.environ.get("NAME_COLUMN", "0"))
EMAIL_COLUMN: int = int(os.environ.get("EMAIL_COLUMN", "1"))
CANVA_DESIGN_ID: str = os.environ.get("CANVA_DESIGN_ID", "")
