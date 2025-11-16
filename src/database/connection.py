"""
Database connection management module.
Provides connection pooling and context managers for database operations.
"""
import logging
import sys
from contextlib import contextmanager
from typing import Optional
from pathlib import Path

import pyodbc

# Smart import: works both when imported and when run directly
try:
    # Try relative import (when imported as module)
    from ..config import Config
except ImportError:
    # Fallback for direct execution
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.config import Config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, config: Config = Config):
        self.config = config
        self._connection_string = config.get_connection_string()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections.
        
        Example:
            >>> with db.get_connection() as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT 1")
        """
        conn = None
        try:
            conn = pyodbc.connect(self._connection_string)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor.
        
        Example:
            >>> with db.get_cursor() as (cursor, conn):
            ...     cursor.execute("SELECT 1")
            ...     result = cursor.fetchone()
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor, conn
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> list:
        """Execute a query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters (optional)
            
        Returns:
            List of result rows
            
        Example:
            >>> results = db.execute_query("SELECT * FROM Posts WHERE id = ?", (1,))
        """
        with self.get_cursor() as (cursor, conn):
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Try to fetch results if it's a SELECT query
            try:
                return cursor.fetchall()
            except pyodbc.ProgrammingError:
                # Not a SELECT query (INSERT, UPDATE, etc.)
                return []
    
    def execute_many(self, query: str, params_list: list[tuple]) -> int:
        """Execute a query with multiple parameter sets.
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        with self.get_cursor() as (cursor, conn):
            cursor.executemany(query, params_list)
            return cursor.rowcount
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        query = """
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = ?
        """
        result = self.execute_query(query, (table_name,))
        return result[0][0] > 0 if result else False
    
    def get_last_insert_id(self, cursor) -> int:
        """Get the last inserted identity value.
        
        Args:
            cursor: Database cursor
            
        Returns:
            Last inserted ID
        """
        cursor.execute("SELECT @@IDENTITY")
        result = cursor.fetchone()
        return result[0] if result else None
    
    def test_connection(self) -> bool:
        """Test database connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Global database manager instance
db = DatabaseManager()


# ═══════════════════════════════════════════════════════════════
# Test/Debug section - only runs when executed directly
# ═══════════════════════════════════════════════════════════════

def run_diagnostics():
    """Run database diagnostics."""
    print("="*70)
    print("🔍 DATABASE CONNECTION DIAGNOSTICS")
    print("="*70)
    
    # 1. Configuration check
    print("\n📋 Configuration:")
    print(f"   Server: {Config.SQL_SERVER}")
    print(f"   Database: {Config.SQL_DATABASE}")
    print(f"   Driver: {Config.SQL_DRIVER}")
    print(f"   Trusted Connection: {Config.SQL_TRUSTED}")
    
    # 2. Connection test
    print("\n🔌 Testing Connection...")
    try:
        with db.get_connection() as conn:
            print("   ✅ Connection successful!")
            
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            print(f"\n📊 SQL Server Version:")
            print(f"   {version[:150]}...")
            
            # Get database info
            cursor.execute("""
                SELECT 
                    name,
                    database_id,
                    create_date,
                    compatibility_level
                FROM sys.databases 
                WHERE name = ?
            """, (Config.SQL_DATABASE,))
            
            db_info = cursor.fetchone()
            if db_info:
                print(f"\n💾 Database Info:")
                print(f"   Name: {db_info.name}")
                print(f"   ID: {db_info.database_id}")
                print(f"   Created: {db_info.create_date}")
                print(f"   Compatibility Level: {db_info.compatibility_level}")
            
    except pyodbc.Error as e:
        print(f"   ❌ Connection failed!")
        print(f"   Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check SQL Server is running")
        print("   2. Verify connection string in .env")
        print("   3. Check ODBC Driver is installed")
        print("   4. Test with: python -m src.cli db")
        return False
    
    # 3. Table check
    print("\n📋 Checking Tables:")
    tables = ['Posts', 'MediaItems', 'Links', 'SocialExtracts', 'JobPosts']
    
    for table in tables:
        exists = db.table_exists(table)
        status = "✅" if exists else "❌"
        print(f"   {status} {table}")
    
    # 4. Quick stats
    print("\n📊 Quick Statistics:")
    try:
        for table in tables:
            if db.table_exists(table):
                result = db.execute_query(f"SELECT COUNT(*) FROM dbo.{table}")
                count = result[0][0] if result else 0
                print(f"   {table}: {count:,} rows")
    except Exception as e:
        print(f"   ⚠️  Could not fetch stats: {e}")
    
    print("\n" + "="*70)
    print("✅ DIAGNOSTICS COMPLETE")
    print("="*70)
    
    return True


if __name__ == "__main__":
    """
    این بخش فقط وقتی اجرا می‌شه که فایل رو مستقیماً run کنید:
    python src/database/connection.py
    """
    import os
    
    print("\n⚠️  WARNING: You're running this file directly!")
    print("📌 Recommended usage:")
    print("   python -m src.cli db")
    print("   python -m src.cli help")
    print("\n" + "-"*70 + "\n")
    
    # Check if .env exists
    env_file = Path(__file__).parent.parent.parent / ".env"
    if not env_file.exists():
        print("❌ .env file not found!")
        print("💡 Copy .env.example to .env and configure it")
        sys.exit(1)
    
    # Run diagnostics
    try:
        success = run_diagnostics()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)