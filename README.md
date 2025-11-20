Social Data Pipeline

This project provides an end-to-end pipeline for collecting, processing, and analyzing job-related content from multiple social media platforms. It integrates scraping tools, text processing modules, and NLP models to convert raw posts into structured job information.

Features
Multi-platform data collection

Telegram channels (real-time and batch modes)

LinkedIn posts

X/Twitter posts

Advanced text and content processing

OCR extraction from images

Automatic translation to Persian

Entity extraction using spaCy

Job information parsing and structuring

Real-time and scheduled workflows

Event-driven Telegram listener

Periodic scraping tasks

Asynchronous processing pipeline

Reliable data storage

SQL Server support

Normalized relational schema with foreign keys

Safe transactions and consistent data handling

Requirements

Python 3.9 or newer

SQL Server 2017+ or Azure SQL Database

ODBC Driver 17 for SQL Server

Tesseract OCR (optional, for image processing)

Chrome/Chromium (for Selenium)

Installation
1. Clone the repository
git clone https://github.com/muhammadseyedi/social-pipeline.git
cd social-pipeline

2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

3. Install dependencies
pip install -r requirements.txt

4. Download the spaCy model
python -m spacy download en_core_web_sm
# For higher accuracy:
# python -m spacy download en_core_web_trf

5. Install Tesseract (optional)

Windows:
https://github.com/UB-Mannheim/tesseract/wiki

Linux:

sudo apt-get install tesseract-ocr


macOS:

brew install tesseract

Configuration
1. Copy the environment template
cp .env.example .env

2. Set up environment variables

Update .env with your settings:

# Telegram API
TG_API_ID=your_api_id
TG_API_HASH=your_api_hash
TG_SESSION_STR=your_session_string
TG_CHANNEL_USERNAME=@YourChannel

# SQL Server
SQL_SERVER=localhost
SQL_DATABASE=SocialDataDB
SQL_TRUSTED=1
# For SQL authentication:
# SQL_TRUSTED=0
# SQL_UID=your_username
# SQL_PWD=your_password

# LinkedIn credentials (optional)
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password

# Tesseract (Windows)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Processing intervals
SCRAPE_INTERVAL=300
PROCESS_INTERVAL=120

# Selenium
SELENIUM_HEADLESS=1

3. Generate a Telegram session string
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = your_api_id
API_HASH = "your_api_hash"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print(client.session.save())

Usage
Initialize the database
python -m src.cli db

Batch operations

Fetch Telegram messages:

python -m src.cli telegram 100


Scrape social media links:

python -m src.cli scrape-x
python -m src.cli scrape-li


Process and translate:

python -m src.cli process


Extract job information:

python -m src.cli populate-jobs
python -m src.cli nlp-run

Real-time mode
python -m src.cli realtime


This mode:

Listens for new Telegram messages

Periodically scrapes pending links

Processes and translates content

Extracts job information

Preview stored data
python -m src.cli preview Posts 10
python -m src.cli preview SocialExtracts 20
python -m src.cli preview JobPosts 15

Database Schema
Posts
  └── MediaItems
        └── Links
              └── SocialExtracts
                    └── JobPosts

Table overview

Posts: Telegram message metadata

MediaItems: images and OCR-extracted text

Links: URLs detected in messages

SocialExtracts: scraped content from external sites

JobPosts: structured job-related fields

Testing

Run tests:

pytest tests/


Run with coverage:

pytest --cov=src tests/

Project Structure
social-pipeline/
├── src/
│   ├── config.py
│   ├── database/
│   │   ├── connection.py
│   │   └── schema.py
│   ├── scrapers/
│   │   ├── telegram.py
│   │   ├── x_scraper.py
│   │   └── linkedin.py
│   ├── processors/
│   │   ├── text_cleaner.py
│   │   ├── translator.py
│   │   └── nlp_processor.py
│   ├── extractors/
│   │   ├── link_extractor.py
│   │   └── job_extractor.py
│   └── cli.py
├── tests/
├── .env.example
├── requirements.txt
└── README.md

Acknowledgments

Telethon (Telegram API client)

spaCy (NLP toolkit)

Selenium (web automation)

pytesseract (OCR engine)

Project link:
https://github.com/muhammadseyedi/social-pipeline