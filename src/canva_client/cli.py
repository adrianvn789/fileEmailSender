"""CLI entry point for canva-client."""
import sys
from canva_client.config import validate_config


def main() -> None:
    """Main CLI entry point. Validates config, then runs pipeline."""
    validate_config()

    from canva_client.pipeline import run_canva_pipeline
    try:
        certificates = run_canva_pipeline()
        if not certificates:
            sys.exit(1)
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nAborted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
