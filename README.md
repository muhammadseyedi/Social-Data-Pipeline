# Social Data Pipeline

A complete data pipeline for collecting, processing, and analyzing
job-related content from social media platforms. The system integrates
scrapers, text-processing components, and NLP models to transform raw
posts into structured, searchable job information.

## Features

### Multi-platform Data Collection

-   Telegram channel scraping (real-time and batch)
-   LinkedIn post extraction
-   X/Twitter post scraping

### Advanced Processing

-   OCR text extraction from images
-   Automatic translation (English → Persian)
-   Entity extraction using spaCy
-   Job information parsing and structuring

### Real-time and Scheduled Workflows

-   Event-driven Telegram listener
-   Scheduled scraping of pending links
-   Asynchronous processing pipeline

### Reliable Data Storage

-   SQL Server integration
-   Normalized relational schema
-   Transaction-safe operations

## Requirements

-   Python 3.9+
-   SQL Server 2017+ or Azure SQL Database
-   ODBC Driver 17 for SQL Server
-   Tesseract OCR (optional)
-   Chrome/Chromium (for Selenium automation)

## Installation

### 1. Clone the repository

``` bash
git clone https://github.com/muhammadseyedi/social-pipeline.git
cd social-pipeline
```

### 2. Create a virtual environment

``` bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

### 4. Download spaCy models

``` bash
python -m spacy download en_core_web_sm
# Optional:
# python -m spacy download en_core_web_trf
```

### 5. Install Tesseract (optional)

Windows:\
https://github.com/UB-Mannheim/tesseract/wiki

Linux:

``` bash
sudo apt-get install tesseract-ocr
```

macOS:

``` bash
brew install tesseract
```

## Configuration

### 1. Copy the environment file

``` bash
cp .env.example .env
```

### 2. Set environment variables

Edit `.env` with your own credentials.

### 3. Generate a Telegram session string

``` python
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = your_api_id
API_HASH = "your_api_hash"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print(client.session.save())
```

## Usage

### Initialize the database

``` bash
python -m src.cli db
```

### Batch operations

``` bash
python -m src.cli telegram 100
python -m src.cli scrape-x
python -m src.cli scrape-li
python -m src.cli process
python -m src.cli populate-jobs
python -m src.cli nlp-run
```

### Real-time mode

``` bash
python -m src.cli realtime
```

### Preview stored data

``` bash
python -m src.cli preview Posts 10
python -m src.cli preview SocialExtracts 20
python -m src.cli preview JobPosts 15
```

## Database Schema

    Posts
     └── MediaItems
           └── Links
                 └── SocialExtracts
                       └── JobPosts

## Testing

``` bash
pytest tests/
pytest --cov=src tests/
```

## Project Structure

    social-pipeline/
    ├── src/
    │   ├── config.py
    │   ├── database/
    │   ├── scrapers/
    │   ├── processors/
    │   ├── extractors/
    │   └── cli.py
    └── tests/

## Acknowledgments

-   Telethon
-   spaCy
-   Selenium
-   pytesseract

Project link: https://github.com/muhammadseyedi/social-pipeline
