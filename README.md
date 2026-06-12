# fileEmailSender

Match certificate PDFs to attendees from an Excel list, then email each person their certificate via Gmail.

Built for events (hackathons, workshops) where you export per-person certificate PDFs (e.g. from Canva) and need to deliver them individually by email.

## How it works

1. **Match** — extracts the recipient name from each PDF, fuzzy-matches it against the attendee list, and writes a reviewable `matches.csv`.
2. **Send** — reads `matches.csv` and emails each attendee their PDF through Gmail. Already-sent emails are logged and skipped on re-runs.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- A Gmail account with an **App Password** (requires 2-Step Verification)

## Installation

```bash
git clone https://github.com/adrianvn789/fileEmailSender.git
cd fileEmailSender
uv sync
```

## Configuration

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `GMAIL_USER` | Your Gmail address | — |
| `GMAIL_APP_PASSWORD` | Gmail App Password (Google Account → Security → 2-Step Verification → App passwords) | — |
| `MATCH_THRESHOLD` | Minimum fuzzy-match score (0–100) to accept a match | `80` |
| `MARKER_STRING` | Custom marker text that precedes the name in the PDF (see below) | built-in `Certificado a:` variants |
| `INPUT_DIR` | Folder containing event subfolders | `input` |
| `OUTPUT_DIR` | Folder where results are written | `output` |

The email subject and body template live in `src/file_email_sender/config.py`.

## Input layout

Create one subfolder per event inside `input/`:

```
input/
└── my-event/
    ├── attendees.xlsx    # column A = name, column B = email, no header row
    ├── cert1.pdf
    ├── cert2.pdf
    └── ...
```

**Excel file:** first sheet, column A holds the attendee name, column B the email. Rows missing either value are skipped.

**Certificate PDFs:** the recipient name is read from the PDF text. The first page should contain a marker line followed by (or ending with) the name. Recognized markers (case-insensitive):

- `Certificado a: <name>` or `Certificado a:` with the name on the next line
- `Certificado:` / `Certifica a:` / `Certifica:` variants, with or without a space before the colon
- `Certificado a` (no colon) at the end of a line, name on the next line

**Custom marker:** if your certificates use different wording, pass it with `--marker` (or set `MARKER_STRING` in `.env`):

```bash
uv run file-email-sender match my-event --marker "Otorgado a"
```

Custom markers are matched case- and accent-insensitively, tolerate extra spaces and an optional colon, and accept the name on the same line or the next line — same robustness as the default. Setting a custom marker replaces the built-in `Certificado a:` variants.

If no marker is found (e.g. image-only PDFs), the **filename** is used as a fallback: name the file with the person's name or part of it (`maria_perez.pdf`, `cert-Maria-Silva.pdf`, `MariaSilva.pdf` — `_`, `-`, `.` count as spaces, camelCase is split).

## Usage

### 1. Match attendees to PDFs

```bash
uv run file-email-sender match my-event
```

If the PDFs live in a different subfolder than the Excel file:

```bash
uv run file-email-sender match my-event my-certs-folder
```

To ignore the PDF text entirely and match every certificate by its **filename**:

```bash
uv run file-email-sender match my-event --by-filename
```

Custom marker wording (see [Input layout](#input-layout)):

```bash
uv run file-email-sender match my-event --marker "Otorgado a"
```

Filename matching is fuzzy, not exact: `cert-MARIA_pérez.pdf`, `MariaPerez.pdf`, or `maria-perez-2024.pdf` all match the attendee `María Perez`. Extra words and numbers in the filename are tolerated.

This writes `output/my-event/matches.csv` and prints matched pairs, unmatched attendees, and unmatched PDFs.

Matching is robust to case, accents, word order, and minor typos (`MARÍA PÉREZ` ≡ `perez maria`). Each PDF is matched to at most one attendee.

### 2. Review matches

Open `output/my-event/matches.csv` and check the pairs before sending — especially rows with a low `score`. Edit or delete rows as needed.

### 3. Send emails

```bash
uv run file-email-sender send
```

Scans every subfolder in `output/`, reads its `matches.csv`, and sends each attendee their PDF. Progress is printed per email, with a 1.5 s delay between sends.

Sent emails are recorded in `matches_log.json` next to the CSV, so re-running is safe: already-sent addresses are skipped.

To use a different CSV file name:

```bash
uv run file-email-sender send other.csv
```

## Running tests

```bash
uv run pytest
```
