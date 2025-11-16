"""
Date parsing and normalization utilities.
Handles various date formats from social media.
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Optional

try:
    from dateutil import parser as dateutil_parser
except ImportError:
    dateutil_parser = None

logger = logging.getLogger(__name__)


class DateParser:
    """Parse and normalize dates from various formats."""
    
    def __init__(self):
        """Initialize date parser."""
        pass
    
    def parse(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to standard format (YYYY-MM-DD HH:MM:SS).
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Normalized date string or None
        """
        if not date_str:
            return None
        
        text = str(date_str).strip()
        
        if not text or text.lower() in ("none", "null"):
            return None
        
        # Clean up common noise
        text = re.sub(r'[\u2022\u200b]+', ' ', text)
        text = re.sub(r'\b(edited|posted|updated|shared|about)\b', '', text, flags=re.I)
        text = text.strip()
        
        # Try ISO format
        try:
            dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        
        # Try dateutil parser (fuzzy)
        if dateutil_parser:
            try:
                dt = dateutil_parser.parse(text, fuzzy=True)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        
        # Try relative formats (2d, 3h, 1w)
        try:
            dt = self._parse_relative(text)
            if dt:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _parse_relative(self, text: str) -> Optional[datetime]:
        """Parse relative date formats like '2d ago', '3h', '1w'.
        
        Args:
            text: Relative date string
            
        Returns:
            Datetime object or None
        """
        if not text:
            return None
        
        text = text.strip().lower()
        
        # Remove common words
        text = re.sub(r'\b(edited|ago|posted|updated|shared|about)\b', '', text).strip()
        
        now = datetime.utcnow()
        
        # Days: 2d, 2 days
        match = re.search(r'(\d+)\s*d(?:ays?)?', text)
        if match:
            days = int(match.group(1))
            return now - timedelta(days=days)
        
        # Hours: 3h, 3 hours
        match = re.search(r'(\d+)\s*h(?:ours?)?', text)
        if match:
            hours = int(match.group(1))
            return now - timedelta(hours=hours)
        
        # Minutes: 15m, 15 minutes
        match = re.search(r'(\d+)\s*m(?:in(?:utes?)?)?', text)
        if match:
            minutes = int(match.group(1))
            return now - timedelta(minutes=minutes)
        
        # Weeks: 1w, 1 week
        match = re.search(r'(\d+)\s*w(?:eeks?)?', text)
        if match:
            weeks = int(match.group(1))
            return now - timedelta(weeks=weeks)
        
        # Textual: yesterday, today
        if re.search(r'\byesterday\b', text):
            return now - timedelta(days=1)
        
        if re.search(r'\btoday\b', text):
            return now
        
        return None
    
    def normalize_linkedin_date(self, date_str: Optional[str]) -> Optional[str]:
        """Normalize LinkedIn-specific date formats.
        
        Args:
            date_str: LinkedIn date string
            
        Returns:
            Normalized date or None
        """
        if not date_str:
            return None
        
        # LinkedIn often has "2d • Edited" format
        text = str(date_str).strip()
        
        # Remove "Edited" and bullet points
        text = re.sub(r'[\u2022•]\s*edited', '', text, flags=re.I)
        text = re.sub(r'[\u2022•]', '', text)
        text = text.strip()
        
        return self.parse(text)
    
    def is_recent(self, date_str: Optional[str], days: int = 30) -> bool:
        """Check if date is within recent days.
        
        Args:
            date_str: Date string
            days: Number of days to consider recent
            
        Returns:
            True if recent, False otherwise
        """
        parsed = self.parse(date_str)
        if not parsed:
            return False
        
        try:
            dt = datetime.strptime(parsed, "%Y-%m-%d %H:%M:%S")
            delta = datetime.utcnow() - dt
            return delta.days <= days
        except Exception:
            return False
    
    def format_for_display(self, date_str: Optional[str]) -> str:
        """Format date for human-readable display.
        
        Args:
            date_str: Date string
            
        Returns:
            Formatted date string
        """
        parsed = self.parse(date_str)
        if not parsed:
            return "Unknown date"
        
        try:
            dt = datetime.strptime(parsed, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%B %d, %Y at %I:%M %p")
        except Exception:
            return parsed
    
    def to_sql_format(self, date_str: Optional[str]) -> Optional[str]:
        """Convert to SQL-compatible format.
        
        Args:
            date_str: Date string
            
        Returns:
            SQL-formatted date string
        """
        return self.parse(date_str)