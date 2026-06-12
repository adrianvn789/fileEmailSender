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

## Step-by-step guide

### Step 1 — Get the code (once)

```bash
git clone https://github.com/adrianvn789/fileEmailSender.git
cd fileEmailSender
uv sync
```

### Step 2 — Configure Gmail (once)

```bash
cp .env.example .env
```

Open `.env` in any editor and fill in:

```
GMAIL_USER=youraddress@gmail.com
GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
```

To get the App Password: Google Account → Security → 2-Step Verification (must be ON) → App passwords → create one → copy the 16-character code.

### Step 3 — Prepare your files

Create a folder for your event inside `input/`:

```
input/
└── my-event/
    ├── attendees.xlsx     ← column A = full name, column B = email, NO header row
    ├── certificado1.pdf
    ├── certificado2.pdf
    └── ...
```

**Excel file:** first sheet, column A holds the attendee name, column B the email. Rows missing either value are skipped.

### Step 4 — Run the matcher

```bash
uv run file-email-sender match my-event
```

This reads each PDF, finds the name after `Certificado a:`, and pairs it with an attendee.

Variants if needed:

- Certificates say something else (e.g. `Otorgado a:`):

  ```bash
  uv run file-email-sender match my-event --marker "Otorgado a"
  ```

- PDFs have no readable text — names are in the filenames:

  ```bash
  uv run file-email-sender match my-event --by-filename
  ```

- Excel file and PDFs live in different subfolders:

  ```bash
  uv run file-email-sender match my-event my-certs-folder
  ```

### Step 5 — Check the results

Open `output/my-event/matches.csv`. Each row = one email that will be sent.

- Verify name ↔ PDF pairs are correct, especially rows with a low `score`
- Delete any row you don't want sent
- The console also lists unmatched attendees and unmatched PDFs

### Step 6 — Send the emails

```bash
uv run file-email-sender send
```

Sends each person their PDF, one every 1.5 seconds, printing SENT/FAIL per person.

### Step 7 — If something fails, run send again

```bash
uv run file-email-sender send
```

Safe to repeat: already-sent people are skipped (tracked in `output/my-event/matches_log.json`).

## How names are read from PDFs

The recipient name is read from the first page of each PDF. Recognized markers (case-insensitive):

- `Certificado a: <name>` or `Certificado a:` with the name on the next line
- `Certificado:` / `Certifica a:` / `Certifica:` variants, with or without a space before the colon
- `Certificado a` (no colon) at the end of a line, name on the next line

**Custom marker:** if your certificates use different wording, pass it with `--marker` (or set `MARKER_STRING` in `.env`). Custom markers are matched case- and accent-insensitively, tolerate extra spaces and an optional colon, and accept the name on the same line or the next line. Setting a custom marker replaces the built-in `Certificado a:` variants.

**Filename fallback:** if no marker is found in the text (e.g. image-only PDFs), the filename is used instead: name the file with the person's name or part of it (`maria_perez.pdf`, `cert-Maria-Silva.pdf`, `MariaSilva.pdf` — `_`, `-`, `.` count as spaces, camelCase is split). With `--by-filename`, the text is skipped and **all** PDFs match this way.

Filename matching is fuzzy, not exact: `cert-MARIA_pérez.pdf`, `MariaPerez.pdf`, or `maria-perez-2024.pdf` all match the attendee `María Perez`. Extra words and numbers in the filename are tolerated.

**Fuzzy matching** is robust to case, accents, word order, and minor typos (`MARÍA PÉREZ` ≡ `perez maria`). Each PDF is matched to at most one attendee.

## Configuration reference

All settings live in `.env`:

| Variable | Description | Default |
|---|---|---|
| `GMAIL_USER` | Your Gmail address | — |
| `GMAIL_APP_PASSWORD` | Gmail App Password | — |
| `MATCH_THRESHOLD` | Minimum fuzzy-match score (0–100) to accept a match | `80` |
| `MARKER_STRING` | Custom marker text that precedes the name in the PDF | built-in `Certificado a:` variants |
| `INPUT_DIR` | Folder containing event subfolders | `input` |
| `OUTPUT_DIR` | Folder where results are written | `output` |

The email subject and body template live in `src/file_email_sender/config.py`.

To use a different CSV file name when sending:

```bash
uv run file-email-sender send other.csv
```

## Running tests

```bash
uv run pytest
```
