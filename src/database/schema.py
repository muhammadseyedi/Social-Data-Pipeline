"""
Database schema management.
Handles table creation and migrations.
"""
import logging

import pyodbc

try:
    from ..config import Config
    from .connection import DatabaseManager
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.config import Config
    from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages database schema creation and migrations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.config = Config
    
    def create_database(self):
        """Create database if it doesn't exist - reads name from Config."""
        db_name = self.config.SQL_DATABASE
        
        # Build master connection string
        if self.config.SQL_TRUSTED:
            master_conn_str = (
                f"DRIVER={self.config.SQL_DRIVER};"
                f"SERVER={self.config.SQL_SERVER};"
                "DATABASE=master;"
                "Trusted_Connection=yes;"
            )
        else:
            master_conn_str = (
                f"DRIVER={self.config.SQL_DRIVER};"
                f"SERVER={self.config.SQL_SERVER};"
                "DATABASE=master;"
                f"UID={self.config.SQL_UID};"
                f"PWD={self.config.SQL_PWD};"
            )
        
        try:
            logger.info(f"Checking/creating database: {db_name}")
            with pyodbc.connect(master_conn_str, autocommit=True) as conn:
                cursor = conn.cursor()
                
                # Check if database exists
                cursor.execute("""
                    SELECT database_id 
                    FROM sys.databases 
                    WHERE name = ?
                """, (db_name,))
                
                exists = cursor.fetchone()
                
                if exists:
                    logger.info(f"Database '{db_name}' already exists.")
                else:
                    # Create database
                    cursor.execute(f"CREATE DATABASE [{db_name}]")
                    logger.info(f"Database '{db_name}' created successfully.")
                    
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise
    
    def create_posts_table(self):
        """Create Posts table."""
        query = """
            IF OBJECT_ID('dbo.Posts', 'U') IS NULL
            CREATE TABLE dbo.Posts (
                id INT IDENTITY(1,1) PRIMARY KEY,
                telegram_message_id BIGINT NOT NULL UNIQUE,
                telegram_date DATETIME NULL,
                source_channel NVARCHAR(200) NULL,
                source_type NVARCHAR(50) NULL,
                created_at DATETIME DEFAULT GETDATE(),
                INDEX idx_telegram_msg_id (telegram_message_id),
                INDEX idx_telegram_date (telegram_date)
            );
        """
        self.db.execute_query(query)
        logger.info("Posts table ensured.")
    
    def create_media_items_table(self):
        """Create MediaItems table."""
        query = """
            IF OBJECT_ID('dbo.MediaItems', 'U') IS NULL
            CREATE TABLE dbo.MediaItems (
                id INT IDENTITY(1,1) PRIMARY KEY,
                post_id BIGINT NULL,
                telegram_message_id BIGINT NULL,
                part_number INT NULL,
                caption NVARCHAR(MAX) NULL,
                image_path NVARCHAR(500) NULL,
                ocr_text NVARCHAR(MAX) NULL,
                created_at DATETIME DEFAULT GETDATE(),
                INDEX idx_post_id (post_id),
                INDEX idx_telegram_msg_id (telegram_message_id)
            );
        """
        self.db.execute_query(query)
        logger.info("MediaItems table ensured.")
    
    def create_links_table(self):
        """Create Links table."""
        query = """
            IF OBJECT_ID('dbo.Links', 'U') IS NULL
            CREATE TABLE dbo.Links (
                id INT IDENTITY(1,1) PRIMARY KEY,
                media_id INT NULL,
                link_url NVARCHAR(1000) NOT NULL,
                link_description NVARCHAR(MAX) NULL,
                Source_Type NVARCHAR(50) NULL,
                InsertedAt DATETIME DEFAULT GETDATE(),
                INDEX idx_media_id (media_id),
                INDEX idx_source_type (Source_Type),
                CONSTRAINT FK_Links_MediaItems FOREIGN KEY (media_id) 
                    REFERENCES dbo.MediaItems(id) ON DELETE CASCADE
            );
        """
        self.db.execute_query(query)
        logger.info("Links table ensured.")
    
    def create_social_extracts_table(self):
        """Create SocialExtracts table."""
        query = """
            IF OBJECT_ID('dbo.SocialExtracts', 'U') IS NULL
            CREATE TABLE dbo.SocialExtracts (
                Id INT IDENTITY(1,1) PRIMARY KEY,
                link_id INT NULL,
                Platform NVARCHAR(50) NULL,
                OriginalLink NVARCHAR(1000) NULL,
                Username NVARCHAR(200) NULL,
                PostDate NVARCHAR(200) NULL,
                PostContent NVARCHAR(MAX) NULL,
                CleanedContent NVARCHAR(MAX) NULL,
                TranslatedFa NVARCHAR(MAX) NULL,
                ProcessedAt DATETIME NULL,
                ExtractedAt DATETIME DEFAULT GETDATE(),
                INDEX idx_link_id (link_id),
                INDEX idx_platform (Platform),
                INDEX idx_processed (ProcessedAt),
                CONSTRAINT FK_SocialExtracts_Links FOREIGN KEY (link_id) 
                    REFERENCES dbo.Links(id) ON DELETE CASCADE
            );
        """
        self.db.execute_query(query)
        logger.info("SocialExtracts table ensured.")
    
    def create_job_posts_table(self):
        """Create JobPosts table with proper field sizes for indexing.
        
        ⚠️ IMPORTANT: NVARCHAR(MAX) cannot be used in indexes!
        Changed Field from NVARCHAR(MAX) to NVARCHAR(200) for indexing.
        """
        query = """
            IF OBJECT_ID('dbo.JobPosts', 'U') IS NULL
            CREATE TABLE dbo.JobPosts (
                Id INT IDENTITY(1,1) PRIMARY KEY,
                PostId BIGINT NULL,
                LinkId INT NULL,
                Title NVARCHAR(500) NULL,
                Employer NVARCHAR(500) NULL,
                University NVARCHAR(500) NULL,
                Location NVARCHAR(200) NULL,
                JobPublishedDate DATETIME NULL,
                TelegramMessageDate DATETIME NULL,
                JobType NVARCHAR(100) NULL,
                Field NVARCHAR(200) NULL,
                ResearchTopic NVARCHAR(MAX) NULL,
                Description NVARCHAR(MAX) NULL,
                SourceType NVARCHAR(100) NULL,
                Links NVARCHAR(1000) NULL,
                IsIncomplete BIT DEFAULT 0,
                CreatedAt DATETIME DEFAULT GETDATE(),
                INDEX idx_link_id (LinkId),
                INDEX idx_job_type (JobType),
                INDEX idx_field (Field),
                INDEX idx_published_date (JobPublishedDate),
                CONSTRAINT FK_JobPosts_Links FOREIGN KEY (LinkId) 
                    REFERENCES dbo.Links(id) ON DELETE SET NULL
            );
        """
        self.db.execute_query(query)
        logger.info("JobPosts table ensured.")
    
    def create_all_tables(self):
        """Create all required tables in correct order."""
        logger.info("Creating database schema...")
        
        try:
            self.create_database()
            self.create_posts_table()
            self.create_media_items_table()
            self.create_links_table()
            self.create_social_extracts_table()
            self.create_job_posts_table()
            
            logger.info("✅ All tables created successfully.")
        except Exception as e:
            logger.error(f"❌ Schema creation failed: {e}")
            raise
    
    def drop_all_tables(self, confirm: bool = False):
        """Drop all tables. Use with caution!
        
        Args:
            confirm: Must be True to actually drop tables
            
        Raises:
            ValueError: If confirm is not True
        """
        if not confirm:
            raise ValueError("Must explicitly confirm table deletion with confirm=True")
        
        logger.warning("⚠️  Dropping all tables...")
        
        tables = [
            "JobPosts", 
            "SocialExtracts", 
            "Links", 
            "MediaItems", 
            "Posts"
        ]
        
        for table in tables:
            try:
                self.db.execute_query(f"DROP TABLE IF EXISTS dbo.{table}")
                logger.info(f"Dropped table: {table}")
            except Exception as e:
                logger.warning(f"Could not drop {table}: {e}")


# Test when run directly
if __name__ == "__main__":
    print("🧪 Testing SchemaManager...")
    
    try:
        db = DatabaseManager()
        schema = SchemaManager(db)
        
        print("\n1️⃣ Creating database and tables...")
        schema.create_all_tables()
        
        print("\n2️⃣ Verifying tables...")
        tables = ['Posts', 'MediaItems', 'Links', 'SocialExtracts', 'JobPosts']
        for table in tables:
            exists = db.table_exists(table)
            status = "✅" if exists else "❌"
            print(f"   {status} {table}")
        
        print("\n✅ Schema test completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()