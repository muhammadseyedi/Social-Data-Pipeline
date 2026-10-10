# Social Data Pipeline

A Python project for collecting job-related posts from social platforms and transforming them into structured records. The repository includes Telegram, LinkedIn, and X/Twitter collection code, OCR helpers, translation/text-cleaning utilities, NLP extraction, and SQL Server persistence.

> **Project status:** this repository requires local credentials, SQL Server, and platform-specific setup. Scrapers can also be affected by external site changes and access restrictions. The documented commands have not been validated here against a freshly provisioned SQL Server environment.

## What it contains

- Telegram message collection and a real-time listener.
- Scraping of links/posts from X and LinkedIn.
- OCR support for downloaded images using Tesseract.
- Text cleaning, translation, and spaCy-based entity extraction.
- SQL Server schema and database access helpers.
- A command-line interface for running the pipeline in stages.

## Requirements

- Python 3.9 or newer.
- SQL Server (local or remote) and a compatible Microsoft ODBC driver.
- Telegram API credentials for Telegram collection.
- Tesseract OCR if you plan to run OCR.
- Chrome/Chromium if required by the Selenium-based scrapers.
- Network access to download Python packages and spaCy's language model.

## Installation

Clone the repository using its actual GitHub URL:

```bash
git clone https://github.com/muhammadseyedi/Social-Data-Pipeline.git
cd Social-Data-Pipeline
python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate
```

Install Python dependencies and the spaCy English model:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Install Tesseract only if you need OCR. On Windows, an installer is available from the [UB Mannheim Tesseract build page](https://github.com/UB-Mannheim/tesseract/wiki); on Debian/Ubuntu, use `sudo apt-get install tesseract-ocr`.

## Configuration

Copy the example environment file and replace placeholder values:

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/macOS
cp .env.example .env
```

At minimum, configure `TG_API_ID`, `TG_API_HASH`, and the SQL Server settings before using the related commands. Use `SQL_TRUSTED=1` for Windows integrated authentication; otherwise set `SQL_TRUSTED=0`, `SQL_UID`, and `SQL_PWD`. Keep real credentials in your local `.env` file only—never commit it.

The code loads `.env` when `python-dotenv` is installed. Environment variables set by your shell are also supported.

For OCR, set `TESSERACT_CMD` to the installed executable path and choose `OCR_LANG` as needed. The default command-line OCR language is English; install the corresponding Tesseract language data if you need another language.

## Usage

Run commands from the repository root:

```bash
# Show all commands
python -m src.cli help

# Create/verify database tables
python -m src.cli db

# Collect Telegram messages (example: 100)
python -m src.cli telegram 100

# Scrape already-collected X and LinkedIn links
python -m src.cli scrape-x
python -m src.cli scrape-li
python -m src.cli scrape-all

# Process extracted text and create job records
python -m src.cli process
python -m src.cli populate-jobs

# Run NLP entity extraction (example limit: 200)
python -m src.cli nlp 200

# Run OCR for images that do not have OCR text
python -m src.cli ocr

# Start the real-time listener and scheduled tasks
python -m src.cli realtime

# Check configuration and database status
python -m src.cli config
python -m src.cli status
```

The commands are stages of a pipeline; configure and verify their prerequisites before running them. The `drop-db` command is destructive and removes database tables, so use it only when you explicitly intend to reset the database.

## Database overview

The main entities are linked in this order:

```text
Posts
└── MediaItems
    └── Links
        └── SocialExtracts
            └── JobPosts
```

The database is created/verified by the `db` command. The SQL Server instance and account must have the permissions required to create and update the project tables.

## Project structure

```text
src/
├── cli.py
├── config.py
├── database/
├── extractors/
├── processors/
├── scrapers/
└── utils/
```

## Testing and limitations

An automated `tests/` suite is not currently included in the repository, so no claim of test-suite coverage is made here. Before using this project for real data collection, test each configured source and database operation in your own environment. External platforms may change their HTML, rate limits, or authentication requirements.

## Acknowledgments

This project uses Telethon, Selenium, spaCy, pytesseract, and other open-source Python libraries.
