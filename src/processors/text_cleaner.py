"""
Text cleaning and normalization module.
Handles various text cleaning operations for social media content.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TextCleaner:
    """Clean and normalize text content from various sources."""
    
    def __init__(self):
        """Initialize text cleaner."""
        pass
    
    def clean_simple(self, text: Optional[str]) -> Optional[str]:
        """Perform simple text cleaning.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text or None
        """
        if not text:
            return None
        
        # Remove carriage returns
        text = re.sub(r'\r', ' ', text)
        
        # Convert markdown links to plain text: [text](url) -> text (url)
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'\1 (\2)', text)
        
        # Collapse multiple newlines
        text = re.sub(r'\n\s*\n+', '\n', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        text = text.strip()
        
        return text if text else None
    
    def clean_linkedin(
        self, 
        text: Optional[str], 
        username: Optional[str] = None
    ) -> Optional[str]:
        """Clean LinkedIn-specific content.
        
        Args:
            text: Raw LinkedIn text
            username: Post author username (for filtering)
            
        Returns:
            Cleaned text
        """
        if not text:
            return None
        
        # Remove common UI noise
        noise_patterns = [
            r'Feed post', r'Follow', r'Your document has finished loading',
            r'Reactions', r'Add a comment', r'Open Emoji Keyboard',
            r'Current selected sort order is .*', r'Edited',
            r'• \d+ (replies|comments|reposts|reactions)',
            r'\d+ reactions', r'\d+ comments', r'\d+ reposts'
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.I)
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
        
        # Filter paragraphs
        filtered = []
        for para in paragraphs:
            # Skip username lines if short
            if username and username.lower() in para.lower() and len(para.split()) < 6:
                continue
            
            # Keep short paragraphs only if they contain important keywords
            if len(para) < 30:
                if re.search(r'apply|application|https?://|#', para, re.I):
                    filtered.append(para)
            else:
                filtered.append(para)
        
        # If nothing left, return longest paragraph
        if not filtered and paragraphs:
            return max(paragraphs, key=len)
        
        # Remove consecutive duplicates
        unique = []
        for para in filtered:
            if not unique or para != unique[-1]:
                unique.append(para)
        
        return "\n\n".join(unique) if unique else None
    
    def clean_username(self, username: Optional[str]) -> Optional[str]:
        """Clean and normalize username.
        
        Args:
            username: Raw username
            
        Returns:
            Cleaned username or None
        """
        if not username:
            return None
        
        text = str(username).strip()
        
        # Remove activity IDs pattern
        if re.fullmatch(r'activity[-_]\d+([A-Za-z0-9_-]+)?', text, flags=re.I):
            return None
        
        if text.lower().startswith('activity-'):
            return None
        
        # Clean activity suffixes
        text = re.sub(r'[_-]activity[-_]\d+([A-Za-z0-9_-]+)?$', '', text, flags=re.I)
        
        # Take first part before underscore
        if '_' in text:
            text = text.split('_', 1)[0].strip()
        
        # Remove hash-like suffixes
        text = re.sub(r'[-_][0-9a-f]{6,}$', '', text, flags=re.I)
        
        # Replace dashes with spaces
        text = text.replace('-', ' ')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Minimum length check
        if len(text) >= 3:
            return text.title()
        
        return None
    
    def normalize_whitespace(self, text: Optional[str]) -> str:
        """Normalize all whitespace in text.
        
        Args:
            text: Text to normalize
            
        Returns:
            Text with normalized whitespace
        """
        if not text:
            return ""
        
        # Remove zero-width characters
        text = re.sub(r'[\u200b\u200c\u200d\x0b\x0c]+', ' ', text)
        
        # Normalize all whitespace to single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def remove_urls(self, text: Optional[str]) -> Optional[str]:
        """Remove URLs from text.
        
        Args:
            text: Text containing URLs
            
        Returns:
            Text without URLs
        """
        if not text:
            return None
        
        # Remove http/https URLs
        text = re.sub(r'https?://[^\s<>"\'()]+', '', text)
        
        # Clean up remaining whitespace
        text = self.normalize_whitespace(text)
        
        return text if text else None
    
    def remove_hashtags(self, text: Optional[str]) -> Optional[str]:
        """Remove hashtags from text.
        
        Args:
            text: Text containing hashtags
            
        Returns:
            Text without hashtags
        """
        if not text:
            return None
        
        # Remove hashtags
        text = re.sub(r'#\w+', '', text)
        
        # Clean up whitespace
        text = self.normalize_whitespace(text)
        
        return text if text else None
    
    def remove_mentions(self, text: Optional[str]) -> Optional[str]:
        """Remove @mentions from text.
        
        Args:
            text: Text containing mentions
            
        Returns:
            Text without mentions
        """
        if not text:
            return None
        
        # Remove @mentions
        text = re.sub(r'@\w+', '', text)
        
        # Clean up whitespace
        text = self.normalize_whitespace(text)
        
        return text if text else None
    
    def remove_emojis(self, text: Optional[str]) -> Optional[str]:
        """Remove emojis from text.
        
        Args:
            text: Text containing emojis
            
        Returns:
            Text without emojis
        """
        if not text:
            return None
        
        # Emoji pattern
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        
        text = emoji_pattern.sub('', text)
        
        # Clean up whitespace
        text = self.normalize_whitespace(text)
        
        return text if text else None
    
    def truncate(
        self, 
        text: Optional[str], 
        max_length: int = 1000,
        suffix: str = "..."
    ) -> Optional[str]:
        """Truncate text to maximum length.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add if truncated
            
        Returns:
            Truncated text
        """
        if not text:
            return None
        
        text = str(text).strip()
        
        if len(text) <= max_length:
            return text
        
        # Truncate and add suffix
        return text[:max_length - len(suffix)] + suffix
    
    def extract_keywords(self, text: Optional[str], min_length: int = 3) -> list[str]:
        """Extract keywords from text.
        
        Args:
            text: Text to extract from
            min_length: Minimum keyword length
            
        Returns:
            List of keywords
        """
        if not text:
            return []
        
        # Remove special characters except spaces
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into words
        words = clean_text.split()
        
        # Filter by length
        keywords = [w for w in words if len(w) >= min_length]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)
        
        return unique_keywords