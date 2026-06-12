"""CLI entry point for canva-client."""
import sys


def main() -> None:
    args = sys.argv[1:]
    command = args[0] if args else "send"

    try:
        if command == "match":
            from canva_client.matcher import run_matching

            attendee_folder = args[1] if len(args) > 1 else None
            cert_folder = args[2] if len(args) > 2 else None
            if not attendee_folder:
                print("Usage: canva-client match <attendee_folder> [certificate_folder]")
                sys.exit(1)
            run_matching(attendee_folder, cert_folder)
        elif command == "send":
            from canva_client.pipeline import run_pipeline

            csv_filename = args[1] if len(args) > 1 else "matches.csv"
            run_pipeline(csv_filename=csv_filename)
        else:
            print(f"Unknown command: {command}")
            print("Usage: canva-client [match|send] ...")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
