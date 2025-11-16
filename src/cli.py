"""
Command-line interface for Social Data Pipeline.
Provides commands for all pipeline operations.
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
from .scrapers.telegram import TelegramScraper
from .scrapers.x_scraper import XScraper
from .scrapers.linkedin import LinkedInScraper
from .processors.text_cleaner import TextCleaner
from .processors.translator import Translator
from .processors.nlp_processor import NLPProcessor
from .extractors.job_extractor import JobExtractor
from .utils.date_parser import DateParser

# Setup logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class CLI:
    """Command-line interface handler."""
    
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

Database Operations:
  db                    - Create database and tables
  drop-db               - Drop all tables (⚠️ destructive!)

Data Collection:
  telegram <n>          - Fetch last n messages from Telegram (default: 50)
  scrape-x              - Scrape pending X/Twitter links
  scrape-li             - Scrape pending LinkedIn links
  scrape-all            - Scrape all pending links (X + LinkedIn)

Processing:
  process               - Clean and translate SocialExtracts
  populate-jobs         - Create JobPosts from SocialExtracts
  nlp-run [limit]       - Run NLP extraction on JobPosts (default: 200)
  update-links          - Update Links descriptions from MediaItems

Real-time:
  realtime              - Start real-time system (listener + periodic tasks)

Utilities:
  preview <table> [n]   - Preview n rows from table (default: 10)
  status                - Show pipeline status
  config                - Show current configuration

Help:
  help                  - Show this menu
  quit, exit            - Exit program

Examples:
  python -m src.cli db
  python -m src.cli telegram 100
  python -m src.cli realtime
  python -m src.cli preview JobPosts 20
        """)
    
    async def cmd_telegram(self, limit: int = 50):
        """Fetch Telegram messages."""
        print(f"\n📥 Fetching {limit} messages from Telegram...")
        
        try:
            scraper = TelegramScraper(self.config, self.db)
            await scraper.fetch_batch(limit=limit)
            print(f"✅ Successfully fetched messages")
        except Exception as e:
            logger.exception("Telegram fetch failed")
            print(f"❌ Error: {e}")
    
    def cmd_scrape_x(self):
        """Scrape X/Twitter links."""
        print("\n🐦 Scraping X/Twitter links...")
        
        try:
            with self.db.get_cursor() as (cur, conn):
                # Get pending X links
                cur.execute("""
                    SELECT l.id, l.link_url
                    FROM dbo.Links l
                    WHERE (l.Source_Type = 'X' OR l.Source_Type = 'Twitter')
                      AND NOT EXISTS (
                          SELECT 1 FROM dbo.SocialExtracts s 
                          WHERE s.OriginalLink = l.link_url
                      )
                """)
                rows = cur.fetchall()
                
                if not rows:
                    print("ℹ️  No pending X links found")
                    return
                
                print(f"Found {len(rows)} pending X links")
                
                with XScraper(self.config) as scraper:
                    for link_id, url in rows:
                        print(f"  🔗 Scraping: {url}")
                        
                        try:
                            data = scraper.scrape_post(url)
                            
                            # Check if already exists
                            cur.execute(
                                "SELECT COUNT(*) FROM dbo.SocialExtracts WHERE OriginalLink = ?",
                                (url,)
                            )
                            
                            if cur.fetchone()[0]:
                                print(f"  ℹ️  Already exists, skipping")
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
                            print(f"  ✅ Saved")
                            
                            # Rate limiting
                            time.sleep(random.uniform(2, 4))
                            
                        except Exception as e:
                            logger.error(f"Error scraping {url}: {e}")
                            print(f"  ❌ Failed: {e}")
                
                print(f"✅ X scraping completed")
        
        except Exception as e:
            logger.exception("X scraping failed")
            print(f"❌ Error: {e}")
    
    def cmd_scrape_linkedin(self):
        """Scrape LinkedIn links."""
        print("\n💼 Scraping LinkedIn links...")
        
        try:
            with self.db.get_cursor() as (cur, conn):
                # Get pending LinkedIn links
                cur.execute("""
                    SELECT l.id, l.link_url
                    FROM dbo.Links l
                    WHERE l.Source_Type = 'LinkedIn'
                      AND NOT EXISTS (
                          SELECT 1 FROM dbo.SocialExtracts s 
                          WHERE s.OriginalLink = l.link_url
                      )
                """)
                rows = cur.fetchall()
                
                if not rows:
                    print("ℹ️  No pending LinkedIn links found")
                    return
                
                print(f"Found {len(rows)} pending LinkedIn links")
                
                with LinkedInScraper(self.config) as scraper:
                    # Login if credentials available
                    if self.config.LINKEDIN_EMAIL and self.config.LINKEDIN_PASSWORD:
                        scraper.login()
                    
                    for link_id, url in rows:
                        print(f"  🔗 Scraping: {url}")
                        
                        try:
                            data = scraper.scrape_post(url)
                            
                            # Check if already exists
                            cur.execute(
                                "SELECT COUNT(*) FROM dbo.SocialExtracts WHERE OriginalLink = ?",
                                (url,)
                            )
                            
                            if cur.fetchone()[0]:
                                print(f"  ℹ️  Already exists, skipping")
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
                            print(f"  ✅ Saved")
                            
                            # Rate limiting
                            time.sleep(random.uniform(3, 6))
                            
                        except Exception as e:
                            logger.error(f"Error scraping {url}: {e}")
                            print(f"  ❌ Failed: {e}")
                
                print(f"✅ LinkedIn scraping completed")
        
        except Exception as e:
            logger.exception("LinkedIn scraping failed")
            print(f"❌ Error: {e}")
    
    def cmd_process(self):
        """Process and translate SocialExtracts."""
        print("\n🔄 Processing SocialExtracts...")
        
        try:
            cleaner = TextCleaner()
            translator = Translator()
            
            with self.db.get_cursor() as (cur, conn):
                cur.execute("""
                    SELECT Id, Platform, Username, PostContent
                    FROM dbo.SocialExtracts
                    WHERE ProcessedAt IS NULL OR TranslatedFa IS NULL
                    ORDER BY Id DESC
                """)
                rows = cur.fetchall()
                
                if not rows:
                    print("ℹ️  No records to process")
                    return
                
                print(f"Processing {len(rows)} records...")
                
                for row in rows:
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
                        translated = translator.translate_to_persian(cleaned, lang)
                    
                    # Update
                    cur.execute("""
                        UPDATE dbo.SocialExtracts
                        SET CleanedContent = ?,
                            TranslatedFa = ?,
                            ProcessedAt = GETDATE()
                        WHERE Id = ?
                    """, (cleaned, translated, record_id))
                    
                    if record_id % 10 == 0:
                        conn.commit()
                        print(f"  Processed {record_id}...")
                
                conn.commit()
                print(f"✅ Processing completed ({len(rows)} records)")
        
        except Exception as e:
            logger.exception("Processing failed")
            print(f"❌ Error: {e}")
    
    def cmd_populate_jobs(self):
        """Populate JobPosts from SocialExtracts."""
        print("\n📋 Populating JobPosts...")
        
        try:
            extractor = JobExtractor(self.db)
            count = extractor.populate_from_social_extracts()
            print(f"✅ Created {count} job posts")
        except Exception as e:
            logger.exception("Job population failed")
            print(f"❌ Error: {e}")
    
    def cmd_nlp_run(self, limit: int = 200):
        """Run NLP extraction on JobPosts."""
        print(f"\n🧠 Running NLP extraction on {limit} job posts...")
        
        try:
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
            with self.db.get_connection() as conn:
                # Posts count
                posts = pd.read_sql("SELECT COUNT(*) as count FROM dbo.Posts", conn).iloc[0]['count']
                print(f"  📨 Posts: {posts:,}")
                
                # Media count
                media = pd.read_sql("SELECT COUNT(*) as count FROM dbo.MediaItems", conn).iloc[0]['count']
                print(f"  🖼️  Media Items: {media:,}")
                
                # Links count
                links = pd.read_sql("SELECT COUNT(*) as count FROM dbo.Links", conn).iloc[0]['count']
                print(f"  🔗 Links: {links:,}")
                
                # Social extracts
                extracts = pd.read_sql("SELECT COUNT(*) as count FROM dbo.SocialExtracts", conn).iloc[0]['count']
                print(f"  📄 Social Extracts: {extracts:,}")
                
                # Job posts
                jobs = pd.read_sql("SELECT COUNT(*) as count FROM dbo.JobPosts", conn).iloc[0]['count']
                print(f"  💼 Job Posts: {jobs:,}")
                
                # Pending processing
                pending = pd.read_sql(
                    "SELECT COUNT(*) as count FROM dbo.SocialExtracts WHERE ProcessedAt IS NULL",
                    conn
                ).iloc[0]['count']
                print(f"\n  ⏳ Pending Processing: {pending:,}")
        
        except ImportError:
            print("❌ pandas required for status. Install with: pip install pandas")
        except Exception as e:
            logger.exception("Status check failed")
            print(f"❌ Error: {e}")
    
    def cmd_config(self):
        """Show configuration."""
        print("\n⚙️  Current Configuration:")
        print(f"  Telegram Channel: {self.config.TG_CHANNEL_USERNAME}")
        print(f"  SQL Server: {self.config.SQL_SERVER}")
        print(f"  SQL Database: {self.config.SQL_DATABASE}")
        print(f"  spaCy Model: {self.config.SPACY_MODEL}")
        print(f"  Selenium Headless: {self.config.SELENIUM_HEADLESS}")
        print(f"  Log Level: {self.config.LOG_LEVEL}")
    
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
            
            elif cmd == 'scrape-x':
                self.cmd_scrape_x()
            
            elif cmd == 'scrape-li':
                self.cmd_scrape_linkedin()
            
            elif cmd == 'scrape-all':
                self.cmd_scrape_x()
                self.cmd_scrape_linkedin()
            
            elif cmd == 'process':
                self.cmd_process()
            
            elif cmd == 'populate-jobs':
                self.cmd_populate_jobs()
            
            elif cmd == 'nlp-run':
                limit = int(args[1]) if len(args) > 1 else 200
                self.cmd_nlp_run(limit)
            
            elif cmd == 'preview':
                table = args[1] if len(args) > 1 else 'SocialExtracts'
                limit = int(args[2]) if len(args) > 2 else 10
                self.cmd_preview(table, limit)
            
            elif cmd == 'status':
                self.cmd_status()
            
            elif cmd == 'config':
                self.cmd_config()
            
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