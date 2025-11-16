"""
Command-line interface for Social Data Pipeline.
Complete implementation with all features.
"""
import sys
import asyncio
import logging
import time
import random
from typing import Optional

from .config import Config
from .database.connection import DatabaseManager
from .database.schema import SchemaManager

# Setup logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class CLI:
    """Command-line interface handler with all features."""
    
    def __init__(self):
        """Initialize CLI."""
        self.config = Config
        self.db = DatabaseManager()
        self.schema = SchemaManager(self.db)
    
    def print_banner(self):
        """Print application banner."""
        print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🚀 Social Data Pipeline v1.0                   ║
║                                                              ║
║   Multi-platform job scraper with NLP & Real-time support   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """)
    
    def print_menu(self):
        """Print command menu."""
        print("""
📋 Available Commands:

🗄️  Database Operations:
  db                      - Create/verify database and tables
  drop-db                 - Drop all tables (⚠️ destructive!)
  status                  - Show pipeline status

📥 Data Collection:
  telegram <n>            - Fetch n messages from Telegram (default: 50)
  scrape-x [limit]        - Scrape pending X/Twitter links
  scrape-li [limit]       - Scrape pending LinkedIn links
  scrape-all              - Scrape all pending links (X + LinkedIn)

🔄 Processing Pipeline:
  process [limit]         - Clean and translate SocialExtracts
  ocr [limit]             - Run OCR on images with missing text
  populate-jobs [limit]   - Create JobPosts from SocialExtracts
  nlp [limit]             - Extract entities with NLP (requires spaCy model)
  
🔧 Maintenance:
  update-links            - Update Links descriptions from MediaItems
  clean-usernames         - Clean and normalize usernames
  fix-dates               - Normalize date formats

⚡ Real-time:
  realtime                - Start real-time system (listener + periodic tasks)

🔍 Utilities:
  preview <table> [n]     - Preview n rows from table
  config                  - Show current configuration
  check-spacy             - Check if spaCy model is installed
  test-telegram           - Test Telegram connection

📚 Help:
  help                    - Show this menu
  quit, exit              - Exit program

Examples:
  python -m src.cli db
  python -m src.cli telegram 100
  python -m src.cli scrape-all
  python -m src.cli process
  python -m src.cli nlp 200
  python -m src.cli status
        """)
    
    async def cmd_telegram(self, limit: int = 50):
        """Fetch Telegram messages with OCR."""
        print(f"\n📥 Fetching {limit} messages from Telegram...")
        
        try:
            from .scrapers.telegram import TelegramScraper
            
            scraper = TelegramScraper(self.config, self.db)
            await scraper.fetch_batch(limit=limit)
            print(f"✅ Successfully fetched {limit} messages")
            
            # Check for images without OCR
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM dbo.MediaItems 
                    WHERE image_path IS NOT NULL 
                      AND ocr_text IS NULL
                """)
                count = cur.fetchone()[0]
                
                if count > 0:
                    print(f"\nℹ️  Found {count} images without OCR")
                    run_ocr = input("Run OCR now? (y/n): ")
                    if run_ocr.lower() == 'y':
                        self.cmd_ocr(count)
                        
        except Exception as e:
            logger.exception("Telegram fetch failed")
            print(f"❌ Error: {e}")
    
    def cmd_ocr(self, limit: Optional[int] = None):
        """Run OCR on images without text."""
        print(f"\n🖼️  Running OCR on images...")
        
        try:
            import pytesseract
            from PIL import Image
            import os
            
            # Check if tesseract is available
            if not os.path.exists(self.config.TESSERACT_CMD):
                print(f"❌ Tesseract not found at: {self.config.TESSERACT_CMD}")
                print("💡 Install Tesseract or update TESSERACT_CMD in .env")
                return
            
            pytesseract.pytesseract.tesseract_cmd = self.config.TESSERACT_CMD
            
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                # Get images without OCR
                query = """
                    SELECT id, image_path 
                    FROM dbo.MediaItems 
                    WHERE image_path IS NOT NULL 
                      AND (ocr_text IS NULL OR ocr_text = '')
                """
                
                if limit:
                    query += f" ORDER BY id DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
                
                cur.execute(query)
                rows = cur.fetchall()
                
                if not rows:
                    print("ℹ️  No images need OCR")
                    return
                
                print(f"Processing {len(rows)} images...")
                processed = 0
                
                for row in rows:
                    media_id = row.id
                    image_path = row.image_path
                    
                    if not os.path.exists(image_path):
                        logger.warning(f"Image not found: {image_path}")
                        continue
                    
                    try:
                        # Run OCR
                        ocr_lang = self.config.OCR_LANG or 'eng'
                        ocr_text = pytesseract.image_to_string(
                            Image.open(image_path),
                            lang=ocr_lang
                        ).strip()
                        
                        if ocr_text:
                            # Update database
                            cur.execute("""
                                UPDATE dbo.MediaItems 
                                SET ocr_text = ? 
                                WHERE id = ?
                            """, (ocr_text, media_id))
                            
                            processed += 1
                            if processed % 10 == 0:
                                conn.commit()
                                print(f"   Processed {processed}/{len(rows)}...")
                    
                    except Exception as e:
                        logger.warning(f"OCR failed for {image_path}: {e}")
                
                conn.commit()
                print(f"✅ OCR completed: {processed}/{len(rows)} images processed")
                
        except ImportError:
            print("❌ pytesseract not installed!")
            print("💡 Install with: pip install pytesseract Pillow")
        except Exception as e:
            logger.exception("OCR failed")
            print(f"❌ Error: {e}")
    
    def cmd_scrape_x(self, limit: Optional[int] = None):
        """Scrape X/Twitter links."""
        print("\n🐦 Scraping X/Twitter links...")
        
        try:
            from .scrapers.x_scraper import XScraper
            
            with self.db.get_cursor() as (cur, conn):
                # Get pending X links
                query = """
                    SELECT l.id, l.link_url
                    FROM dbo.Links l
                    WHERE (l.Source_Type = 'X' OR l.Source_Type = 'Twitter')
                      AND NOT EXISTS (
                          SELECT 1 FROM dbo.SocialExtracts s 
                          WHERE s.OriginalLink = l.link_url
                      )
                """
                
                if limit:
                    query += f" ORDER BY l.id DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
                
                cur.execute(query)
                rows = cur.fetchall()
                
                if not rows:
                    print("ℹ️  No pending X links found")
                    return
                
                print(f"Found {len(rows)} pending X links")
                
                with XScraper(self.config) as scraper:
                    for i, (link_id, url) in enumerate(rows, 1):
                        print(f"  [{i}/{len(rows)}] 🔗 {url[:60]}...")
                        
                        try:
                            data = scraper.scrape_post(url)
                            
                            # Check if already exists
                            cur.execute(
                                "SELECT COUNT(*) FROM dbo.SocialExtracts WHERE OriginalLink = ?",
                                (url,)
                            )
                            
                            if cur.fetchone()[0]:
                                print(f"       ℹ️  Already exists, skipping")
                                continue
                            
                            # Insert
                            cur.execute("""
                                INSERT INTO dbo.SocialExtracts 
                                (link_id, Platform, OriginalLink, Username, PostDate, PostContent, ExtractedAt)
                                VALUES (?, ?, ?, ?, ?, ?, GETDATE())
                            """, (
                                link_id,
                                'X',
                                url,
                                data.get('Username'),
                                data.get('PostDate'),
                                data.get('PostContent')
                            ))
                            
                            conn.commit()
                            print(f"       ✅ Saved")
                            
                            # Rate limiting
                            time.sleep(random.uniform(2, 4))
                            
                        except Exception as e:
                            logger.error(f"Error scraping {url}: {e}")
                            print(f"       ❌ Failed: {e}")
                
                print(f"✅ X scraping completed")
        
        except Exception as e:
            logger.exception("X scraping failed")
            print(f"❌ Error: {e}")
    
    def cmd_scrape_linkedin(self, limit: Optional[int] = None):
        """Scrape LinkedIn links."""
        print("\n💼 Scraping LinkedIn links...")
        
        try:
            from .scrapers.linkedin import LinkedInScraper
            
            with self.db.get_cursor() as (cur, conn):
                # Get pending LinkedIn links
                query = """
                    SELECT l.id, l.link_url
                    FROM dbo.Links l
                    WHERE l.Source_Type = 'LinkedIn'
                      AND NOT EXISTS (
                          SELECT 1 FROM dbo.SocialExtracts s 
                          WHERE s.OriginalLink = l.link_url
                      )
                """
                
                if limit:
                    query += f" ORDER BY l.id DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
                
                cur.execute(query)
                rows = cur.fetchall()
                
                if not rows:
                    print("ℹ️  No pending LinkedIn links found")
                    return
                
                print(f"Found {len(rows)} pending LinkedIn links")
                
                with LinkedInScraper(self.config) as scraper:
                    # Login if credentials available
                    if self.config.LINKEDIN_EMAIL and self.config.LINKEDIN_PASSWORD:
                        print("🔐 Logging into LinkedIn...")
                        scraper.login()
                    
                    for i, (link_id, url) in enumerate(rows, 1):
                        print(f"  [{i}/{len(rows)}] 🔗 {url[:60]}...")
                        
                        try:
                            data = scraper.scrape_post(url)
                            
                            # Check if already exists
                            cur.execute(
                                "SELECT COUNT(*) FROM dbo.SocialExtracts WHERE OriginalLink = ?",
                                (url,)
                            )
                            
                            if cur.fetchone()[0]:
                                print(f"       ℹ️  Already exists, skipping")
                                continue
                            
                            # Insert
                            cur.execute("""
                                INSERT INTO dbo.SocialExtracts 
                                (link_id, Platform, OriginalLink, Username, PostDate, PostContent, ExtractedAt)
                                VALUES (?, ?, ?, ?, ?, ?, GETDATE())
                            """, (
                                link_id,
                                'LinkedIn',
                                url,
                                data.get('Username'),
                                data.get('PostDate'),
                                data.get('PostContent')
                            ))
                            
                            conn.commit()
                            print(f"       ✅ Saved")
                            
                            # Rate limiting
                            time.sleep(random.uniform(3, 6))
                            
                        except Exception as e:
                            logger.error(f"Error scraping {url}: {e}")
                            print(f"       ❌ Failed: {e}")
                
                print(f"✅ LinkedIn scraping completed")
        
        except Exception as e:
            logger.exception("LinkedIn scraping failed")
            print(f"❌ Error: {e}")
    
    def cmd_process(self, limit: Optional[int] = None):
        """Process and translate SocialExtracts."""
        print("\n🔄 Processing and translating SocialExtracts...")
        
        try:
            from .processors.text_cleaner import TextCleaner
            from .processors.translator import Translator
            
            cleaner = TextCleaner()
            translator = Translator()
            
            # First clean usernames
            print("1️⃣ Cleaning usernames...")
            self.cmd_clean_usernames()
            
            # Then fix dates
            print("\n2️⃣ Normalizing dates...")
            self.cmd_fix_dates()
            
            # Now process content
            print("\n3️⃣ Processing content...")
            
            with self.db.get_cursor() as (cur, conn):
                query = """
                    SELECT Id, Platform, Username, PostContent
                    FROM dbo.SocialExtracts
                    WHERE ProcessedAt IS NULL OR TranslatedFa IS NULL
                    ORDER BY CASE WHEN PostDate IS NULL THEN 1 ELSE 0 END, Id DESC
                """
                
                if limit:
                    query = f"SELECT TOP {limit} * FROM ({query}) AS subquery"
                
                cur.execute(query)
                rows = cur.fetchall()
                
                if not rows:
                    print("ℹ️  No records to process")
                    return
                
                print(f"Processing {len(rows)} records...")
                
                for i, row in enumerate(rows, 1):
                    record_id = row.Id
                    platform = row.Platform
                    username = row.Username
                    raw_content = row.PostContent or ""
                    
                    # Clean
                    if platform and platform.lower() == 'linkedin':
                        cleaned = cleaner.clean_linkedin(raw_content, username)
                    else:
                        cleaned = cleaner.clean_simple(raw_content)
                    
                    # Translate
                    translated = None
                    if cleaned:
                        lang = translator.detect_language(cleaned)
                        if not translator.is_persian(cleaned):
                            translated = translator.translate_to_persian(cleaned, lang)
                    
                    # Update
                    cur.execute("""
                        UPDATE dbo.SocialExtracts
                        SET CleanedContent = ?,
                            TranslatedFa = ?,
                            ProcessedAt = GETDATE()
                        WHERE Id = ?
                    """, (cleaned, translated, record_id))
                    
                    if i % 10 == 0:
                        conn.commit()
                        print(f"   Processed {i}/{len(rows)}...")
                
                conn.commit()
                print(f"✅ Processing completed: {len(rows)} records")
        
        except Exception as e:
            logger.exception("Processing failed")
            print(f"❌ Error: {e}")
    
    def cmd_populate_jobs(self, limit: Optional[int] = None):
        """Populate JobPosts from SocialExtracts."""
        print("\n📋 Populating JobPosts...")
        
        try:
            from .extractors.job_extractor import JobExtractor
            
            extractor = JobExtractor(self.db)
            count = extractor.populate_from_social_extracts(limit)
            print(f"✅ Created {count} job posts")
        except Exception as e:
            logger.exception("Job population failed")
            print(f"❌ Error: {e}")
    
    def cmd_nlp(self, limit: int = 200):
        """Run NLP extraction on JobPosts."""
        print(f"\n🧠 Running NLP extraction on {limit} job posts...")
        
        # Check if spaCy model is installed
        if not self.check_spacy_model(silent=True):
            print(f"\n❌ spaCy model '{self.config.SPACY_MODEL}' not installed!")
            print(f"💡 Install with: python -m spacy download {self.config.SPACY_MODEL}")
            return
        
        try:
            from .extractors.job_extractor import JobExtractor
            
            extractor = JobExtractor(self.db)
            result = extractor.process_nlp_extraction(limit=limit, dry_run=False)
            
            print(f"✅ Updated {result['updated']} job posts")
            
            if result.get('preview'):
                print("\n📊 Sample results:")
                for item in result['preview'][:5]:
                    print(f"  • ID {item['Id']}:")
                    print(f"    University: {item.get('University')}")
                    print(f"    Field: {item.get('Field')}")
                    print(f"    JobType: {item.get('JobType')}")
                    print()
        
        except Exception as e:
            logger.exception("NLP extraction failed")
            print(f"❌ Error: {e}")
    
    def cmd_clean_usernames(self):
        """Clean and normalize usernames."""
        try:
            with self.db.get_cursor() as (cur, conn):
                from .processors.text_cleaner import TextCleaner
                cleaner = TextCleaner()
                
                cur.execute("SELECT Id, Username FROM dbo.SocialExtracts")
                rows = cur.fetchall()
                
                updated = 0
                for row in rows:
                    old_username = row.Username
                    new_username = cleaner.clean_username(old_username)
                    
                    if new_username != old_username:
                        cur.execute(
                            "UPDATE dbo.SocialExtracts SET Username = ? WHERE Id = ?",
                            (new_username, row.Id)
                        )
                        updated += 1
                
                conn.commit()
                print(f"   ✅ Cleaned {updated} usernames")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    def cmd_fix_dates(self):
        """Normalize date formats."""
        try:
            from .utils.date_parser import DateParser
            parser = DateParser()
            
            with self.db.get_cursor() as (cur, conn):
                cur.execute("SELECT Id, PostDate FROM dbo.SocialExtracts")
                rows = cur.fetchall()
                
                updated = 0
                for row in rows:
                    old_date = row.PostDate
                    new_date = parser.parse(old_date)
                    
                    if new_date and new_date != old_date:
                        cur.execute(
                            "UPDATE dbo.SocialExtracts SET PostDate = ? WHERE Id = ?",
                            (new_date, row.Id)
                        )
                        updated += 1
                
                conn.commit()
                print(f"   ✅ Normalized {updated} dates")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    def cmd_update_links(self):
        """Update Links descriptions from MediaItems."""
        print("\n🔗 Updating Links descriptions...")
        
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE L
                SET L.link_description = M.caption
                FROM dbo.Links L
                INNER JOIN dbo.MediaItems M ON L.media_id = M.id
                WHERE L.media_id IS NOT NULL 
                  AND M.caption IS NOT NULL
                  AND (L.link_description IS NULL OR L.link_description = '')
            """)
            updated = cur.rowcount
            conn.commit()
        
        print(f"✅ Updated {updated} link descriptions")
    
    def cmd_preview(self, table: str, limit: int = 10):
        """Preview table data."""
        print(f"\n👀 Previewing {table} (limit: {limit})...")
        
        try:
            import pandas as pd
            
            with self.db.get_connection() as conn:
                df = pd.read_sql(f"SELECT TOP {limit} * FROM dbo.{table}", conn)
                print(df.to_string())
        
        except ImportError:
            print("❌ pandas not installed. Install with: pip install pandas")
        except Exception as e:
            logger.exception("Preview failed")
            print(f"❌ Error: {e}")
    
    def cmd_status(self):
        """Show pipeline status."""
        print("\n📊 Pipeline Status:")
        
        try:
            import pandas as pd
            
            with self.db.get_connection() as conn:
                # Table counts
                tables = ['Posts', 'MediaItems', 'Links', 'SocialExtracts', 'JobPosts']
                
                for table in tables:
                    result = pd.read_sql(
                        f"SELECT COUNT(*) as count FROM dbo.{table}", 
                        conn
                    )
                    count = result.iloc[0]['count']
                    
                    emoji = {
                        'Posts': '📨',
                        'MediaItems': '🖼️',
                        'Links': '🔗',
                        'SocialExtracts': '📄',
                        'JobPosts': '💼'
                    }.get(table, '📊')
                    
                    print(f"  {emoji} {table}: {count:,}")
                
                # Pending processing
                pending = pd.read_sql(
                    "SELECT COUNT(*) as count FROM dbo.SocialExtracts WHERE ProcessedAt IS NULL",
                    conn
                ).iloc[0]['count']
                
                print(f"\n  ⏳ Pending Processing: {pending:,}")
                
                # Images without OCR
                no_ocr = pd.read_sql("""
                    SELECT COUNT(*) as count 
                    FROM dbo.MediaItems 
                    WHERE image_path IS NOT NULL 
                      AND (ocr_text IS NULL OR ocr_text = '')
                """, conn).iloc[0]['count']
                
                print(f"  🖼️  Images without OCR: {no_ocr:,}")
        
        except ImportError:
            print("❌ pandas required. Install with: pip install pandas")
        except Exception as e:
            logger.exception("Status check failed")
            print(f"❌ Error: {e}")
    
    def cmd_config(self):
        """Show configuration."""
        self.config.print_config()
    
    def check_spacy_model(self, silent: bool = False) -> bool:
        """Check if spaCy model is installed."""
        try:
            import spacy
            spacy.load(self.config.SPACY_MODEL)
            if not silent:
                print(f"✅ spaCy model '{self.config.SPACY_MODEL}' is installed")
            return True
        except OSError:
            if not silent:
                print(f"❌ spaCy model '{self.config.SPACY_MODEL}' not found")
                print(f"💡 Install with: python -m spacy download {self.config.SPACY_MODEL}")
            return False
        except ImportError:
            if not silent:
                print("❌ spaCy not installed")
                print("💡 Install with: pip install spacy")
            return False
    
    def cmd_test_telegram(self):
        """Test Telegram connection."""
        print("\n📱 Testing Telegram connection...")
        print("💡 Run: python test_telegram.py")
    
    def run(self, args: list):
        """Run CLI with arguments."""
        if not args:
            self.print_banner()
            self.print_menu()
            return
        
        cmd = args[0].lower()
        
        try:
            if cmd in ('help', '--help', '-h'):
                self.print_menu()
            
            elif cmd == 'db':
                print("\n🔧 Creating database and tables...")
                self.schema.create_all_tables()
            
            elif cmd == 'drop-db':
                confirm = input("⚠️  This will DROP ALL TABLES. Type 'YES' to confirm: ")
                if confirm == 'YES':
                    self.schema.drop_all_tables(confirm=True)
                    print("✅ All tables dropped")
                else:
                    print("❌ Cancelled")
            
            elif cmd == 'telegram':
                limit = int(args[1]) if len(args) > 1 else 50
                asyncio.run(self.cmd_telegram(limit))
            
            elif cmd == 'ocr':
                limit = int(args[1]) if len(args) > 1 else None
                self.cmd_ocr(limit)
            
            elif cmd == 'scrape-x':
                limit = int(args[1]) if len(args) > 1 else None
                self.cmd_scrape_x(limit)
            
            elif cmd == 'scrape-li':
                limit = int(args[1]) if len(args) > 1 else None
                self.cmd_scrape_linkedin(limit)
            
            elif cmd == 'scrape-all':
                self.cmd_scrape_x()
                self.cmd_scrape_linkedin()
            
            elif cmd == 'process':
                limit = int(args[1]) if len(args) > 1 else None
                self.cmd_process(limit)
            
            elif cmd == 'populate-jobs':
                limit = int(args[1]) if len(args) > 1 else None
                self.cmd_populate_jobs(limit)
            
            elif cmd == 'nlp':
                limit = int(args[1]) if len(args) > 1 else 200
                self.cmd_nlp(limit)
            
            elif cmd == 'update-links':
                self.cmd_update_links()
            
            elif cmd == 'clean-usernames':
                print("\n🧹 Cleaning usernames...")
                self.cmd_clean_usernames()
            
            elif cmd == 'fix-dates':
                print("\n📅 Fixing dates...")
                self.cmd_fix_dates()
            
            elif cmd == 'preview':
                table = args[1] if len(args) > 1 else 'SocialExtracts'
                limit = int(args[2]) if len(args) > 2 else 10
                self.cmd_preview(table, limit)
            
            elif cmd == 'status':
                self.cmd_status()
            
            elif cmd == 'config':
                self.cmd_config()
            
            elif cmd == 'check-spacy':
                self.check_spacy_model()
            
            elif cmd == 'test-telegram':
                self.cmd_test_telegram()
            
            elif cmd in ('quit', 'exit'):
                print("\n👋 Goodbye!")
                sys.exit(0)
            
            else:
                print(f"❌ Unknown command: {cmd}")
                print("Run 'help' for available commands")
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
        except Exception as e:
            logger.exception("Command failed")
            print(f"\n❌ Error: {e}")


def main():
    """Main entry point."""
    cli = CLI()
    cli.run(sys.argv[1:])


if __name__ == "__main__":
    main()