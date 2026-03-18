"""CLI entry point for canva-client."""
import sys
from canva_client.config import validate_config


def main() -> None:
    """Main CLI entry point. Validates config, then runs pipeline."""
    validate_config()
    print("canva-client: config OK")
    sys.exit(0)
