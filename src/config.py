"""
Configuration module for Social Data Pipeline.
Loads settings from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from typing import Optional

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    
    # Find .env file
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    # python-dotenv not installed, will use system environment variables
    pass


class Config:
    """Central configuration class for the pipeline."""
    
    # Project paths
    BASE_DIR = Path(__file__).parent.parent
    MEDIA_DIR = Path(os.getenv("MEDIA_DIR", BASE_DIR / "media"))
    
    # ═══════════════════════════════════════════════════════════
    # Telegram configuration
    # ═══════════════════════════════════════════════════════════
    TG_API_ID: int = int(os.getenv("TG_API_ID", "0"))
    TG_API_HASH: str = os.getenv("TG_API_HASH", "")
    TG_SESSION_STR: str = os.getenv("TG_SESSION_STR", "")
    TG_CHANNEL_USERNAME: str = os.getenv("TG_CHANNEL_USERNAME", "@FarasatApplyAcademy")
    
    # ═══════════════════════════════════════════════════════════
    # SQL Server configuration
    # ═══════════════════════════════════════════════════════════
    SQL_SERVER: str = os.getenv("SQL_SERVER", "localhost")
    SQL_DATABASE: str = os.getenv("SQL_DATABASE", "SocialDataDB")
    SQL_DRIVER: str = os.getenv("SQL_DRIVER", "{ODBC Driver 17 for SQL Server}")
    SQL_TRUSTED: bool = os.getenv("SQL_TRUSTED", "1") == "1"
    SQL_UID: str = os.getenv("SQL_UID", "")
    SQL_PWD: str = os.getenv("SQL_PWD", "")
    
    # ═══════════════════════════════════════════════════════════
    # LinkedIn credentials
    # ═══════════════════════════════════════════════════════════
    LINKEDIN_EMAIL: str = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD", "")
    
    # ═══════════════════════════════════════════════════════════
    # OCR configuration
    # ═══════════════════════════════════════════════════════════
    TESSERACT_CMD: str = os.getenv(
        "TESSERACT_CMD", 
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )
    OCR_LANG: Optional[str] = os.getenv("OCR_LANG", None)
    
    # ═══════════════════════════════════════════════════════════
    # NLP configuration
    # ═══════════════════════════════════════════════════════════
    SPACY_MODEL: str = os.getenv("SPACY_MODEL", "en_core_web_sm")
    USE_SPACYTEXTBLOB: bool = os.getenv("USE_SPACYTEXTBLOB", "0") == "1"
    
    # ═══════════════════════════════════════════════════════════
    # Selenium configuration
    # ═══════════════════════════════════════════════════════════
    SELENIUM_HEADLESS: bool = os.getenv("SELENIUM_HEADLESS", "1") == "1"
    
    # ═══════════════════════════════════════════════════════════
    # Real-time intervals (seconds)
    # ═══════════════════════════════════════════════════════════
    SCRAPE_INTERVAL: int = int(os.getenv("SCRAPE_INTERVAL", str(60 * 5)))   # 5 minutes
    PROCESS_INTERVAL: int = int(os.getenv("PROCESS_INTERVAL", str(60 * 2))) # 2 minutes
    
    # ═══════════════════════════════════════════════════════════
    # Logging
    # ═══════════════════════════════════════════════════════════
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration and return list of errors."""
        errors = []
        
        if not cls.TG_API_ID or cls.TG_API_ID == 0:
            errors.append("Telegram API ID (TG_API_ID) is required and must be non-zero")
        
        if not cls.TG_API_HASH:
            errors.append("Telegram API Hash (TG_API_HASH) is required")
        
        if not cls.SQL_SERVER or not cls.SQL_DATABASE:
            errors.append("SQL Server configuration (SQL_SERVER, SQL_DATABASE) is incomplete")
        
        return errors
    
    @classmethod
    def get_connection_string(cls) -> str:
        """Build SQL Server connection string."""
        if cls.SQL_TRUSTED:
            return (
                f"DRIVER={cls.SQL_DRIVER};"
                f"SERVER={cls.SQL_SERVER};"
                f"DATABASE={cls.SQL_DATABASE};"
                "Trusted_Connection=yes;"
            )
        else:
            return (
                f"DRIVER={cls.SQL_DRIVER};"
                f"SERVER={cls.SQL_SERVER};"
                f"DATABASE={cls.SQL_DATABASE};"
                f"UID={cls.SQL_UID};"
                f"PWD={cls.SQL_PWD};"
            )
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)."""
        print("="*70)
        print("⚙️  CURRENT CONFIGURATION")
        print("="*70)
        print(f"\n📱 Telegram:")
        print(f"   API ID: {cls.TG_API_ID}")
        print(f"   API Hash: {cls.TG_API_HASH[:10]}... ({len(cls.TG_API_HASH)} chars)")
        print(f"   Session: {cls.TG_SESSION_STR[:20]}... ({len(cls.TG_SESSION_STR)} chars)")
        print(f"   Channel: {cls.TG_CHANNEL_USERNAME}")
        
        print(f"\n💾 Database:")
        print(f"   Server: {cls.SQL_SERVER}")
        print(f"   Database: {cls.SQL_DATABASE}")
        print(f"   Auth: {'Windows' if cls.SQL_TRUSTED else 'SQL'}")
        
        print(f"\n🔧 Other:")
        print(f"   Headless: {cls.SELENIUM_HEADLESS}")
        print(f"   spaCy Model: {cls.SPACY_MODEL}")
        print(f"   Log Level: {cls.LOG_LEVEL}")
        
        errors = cls.validate()
        if errors:
            print(f"\n⚠️  Configuration Errors:")
            for error in errors:
                print(f"   ❌ {error}")
        else:
            print(f"\n✅ Configuration is valid!")


# Initialize directories on import
Config.ensure_directories()


# Test/Debug when run directly
if __name__ == "__main__":
    print("🧪 Testing Configuration...")
    Config.print_config()
    
    errors = Config.validate()
    if errors:
        print("\n❌ Configuration has errors!")
        for error in errors:
            print(f"   • {error}")
    else:
        print("\n✅ Configuration is ready!")