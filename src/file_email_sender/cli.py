"""CLI entry point for file-email-sender."""
import sys


def main() -> None:
    args = sys.argv[1:]
    by_filename = "--by-filename" in args
    args = [a for a in args if a != "--by-filename"]

    marker = None
    if "--marker" in args:
        idx = args.index("--marker")
        if idx + 1 >= len(args):
            print("Error: --marker requires a value, e.g. --marker 'Otorgado a'")
            sys.exit(1)
        marker = args[idx + 1]
        del args[idx : idx + 2]

    command = args[0] if args else "send"

    try:
        if command == "match":
            from file_email_sender.matcher import run_matching

            attendee_folder = args[1] if len(args) > 1 else None
            cert_folder = args[2] if len(args) > 2 else None
            if not attendee_folder:
                print(
                    "Usage: file-email-sender match <attendee_folder>"
                    " [certificate_folder] [--by-filename] [--marker <string>]"
                )
                sys.exit(1)
            run_matching(
                attendee_folder, cert_folder, by_filename=by_filename, marker=marker
            )
        elif command == "send":
            from file_email_sender.pipeline import run_pipeline

            csv_filename = args[1] if len(args) > 1 else "matches.csv"
            run_pipeline(csv_filename=csv_filename)
        else:
            print(f"Unknown command: {command}")
            print("Usage: file-email-sender [match|send] ...")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
