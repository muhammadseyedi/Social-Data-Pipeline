# 🚀 Social Data Pipeline

A comprehensive data pipeline for scraping, processing, and analyzing job postings from social media platforms (Telegram, LinkedIn, X/Twitter) with advanced NLP capabilities.

## ✨ Features

- **📱 Multi-Platform Scraping**
  - Telegram channels (real-time + batch)
  - LinkedIn posts
  - X/Twitter posts
  
- **🤖 Advanced Processing**
  - OCR text extraction from images
  - Automatic translation (to Persian)
  - NLP entity extraction (spaCy)
  - Job information extraction
  
- **⚡ Real-time & Batch Processing**
  - Event-driven Telegram listener
  - Periodic scraping schedulers
  - Asynchronous processing pipeline
  
- **💾 Robust Data Storage**
  - SQL Server integration
  - Normalized schema with foreign keys
  - Transaction management

## 📋 Requirements

- Python 3.9+
- SQL Server 2017+ or Azure SQL Database
- ODBC Driver 17 for SQL Server
- Tesseract OCR (optional, for image processing)
- Chrome/Chromium (for Selenium)

## 🔧 Installation

### 1. Clone the repository

```bash
git clone https://github.com/muhammadseyedi/social-pipeline.git
cd social-pipeline
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download spaCy model

```bash
python -m spacy download en_core_web_sm
# For better accuracy (optional):
# python -m spacy download en_core_web_trf
```

### 5. Install Tesseract (optional)

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

## ⚙️ Configuration

### 1. Copy environment template

```bash
cp .env.example .env
```

### 2. Configure environment variables

Edit `.env` file with your credentials:

```env
# Telegram API (get from https://my.telegram.org)
TG_API_ID=your_api_id
TG_API_HASH=your_api_hash
TG_SESSION_STR=your_session_string
TG_CHANNEL_USERNAME=@YourChannel

# SQL Server
SQL_SERVER=localhost
SQL_DATABASE=SocialDataDB
SQL_TRUSTED=1  # Use Windows Authentication
# Or use SQL Authentication:
# SQL_TRUSTED=0
# SQL_UID=your_username
# SQL_PWD=your_password

# LinkedIn (optional, for scraping)
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password

# Tesseract path (Windows)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Processing intervals (seconds)
SCRAPE_INTERVAL=300  # 5 minutes
PROCESS_INTERVAL=120  # 2 minutes

# Selenium
SELENIUM_HEADLESS=1  # Run browser in headless mode
```

### 3. Generate Telegram Session String

```python
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = your_api_id
API_HASH = "your_api_hash"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("Your session string:")
    print(client.session.save())
```

## 🚀 Usage

### Initialize Database

```bash
python -m src.cli db
```

### Batch Operations

**Fetch Telegram messages:**
```bash
python -m src.cli telegram 100  # Fetch last 100 messages
```

**Scrape social media links:**
```bash
python -m src.cli scrape-x      # Scrape X/Twitter
python -m src.cli scrape-li     # Scrape LinkedIn
```

**Process and translate:**
```bash
python -m src.cli process
```

**Extract job information:**
```bash
python -m src.cli populate-jobs  # Create job records
python -m src.cli nlp-run        # Run NLP extraction
```

### Real-time Mode

Start the real-time pipeline (Telegram listener + periodic scrapers):

```bash
python -m src.cli realtime
```

This will:
- ✅ Listen for new Telegram messages
- ✅ Periodically scrape pending links
- ✅ Process and translate content
- ✅ Extract job information

### Preview Data

```bash
python -m src.cli preview Posts 10
python -m src.cli preview SocialExtracts 20
python -m src.cli preview JobPosts 15
```

## 📊 Database Schema

```
Posts (Telegram messages)
  └─ MediaItems (images/captions)
      └─ Links (extracted URLs)
          └─ SocialExtracts (scraped content)
              └─ JobPosts (structured job data)
```

### Tables

- **Posts**: Telegram message metadata
- **MediaItems**: Media files and captions with OCR text
- **Links**: Extracted URLs with descriptions
- **SocialExtracts**: Scraped content from social platforms
- **JobPosts**: Structured job posting information

## 🧪 Testing

Run tests:

```bash
pytest tests/
```

Run with coverage:

```bash
pytest --cov=src tests/
```

## 📝 Project Structure

```
social-pipeline/
├── src/
│   ├── config.py              # Configuration management
│   ├── database/
│   │   ├── connection.py      # Database connections
│   │   └── schema.py          # Schema management
│   ├── scrapers/
│   │   ├── telegram.py        # Telegram scraper
│   │   ├── x_scraper.py       # X/Twitter scraper
│   │   └── linkedin.py        # LinkedIn scraper
│   ├── processors/
│   │   ├── text_cleaner.py    # Text cleaning
│   │   ├── translator.py      # Translation
│   │   └── nlp_processor.py   # NLP extraction
│   ├── extractors/
│   │   ├── link_extractor.py  # Link extraction
│   │   └── job_extractor.py   # Job info extraction
│   └── cli.py                 # Command-line interface
├── tests/                     # Test suite
├── .env.example              # Environment template
├── requirements.txt          # Dependencies
└── README.md                 # This file
```



## 🙏 Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram client
- [spaCy](https://spacy.io/) - NLP processing
- [Selenium](https://www.selenium.dev/) - Web scraping
- [pytesseract](https://github.com/madmaze/pytesseract) - OCR



 

Project Link: [https://github.com/muhammadseyedi/social-pipeline](https://github.com/muhammadseyedi/social-pipeline)





Made with ❤️ for the academic community