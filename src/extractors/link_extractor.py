"""
Link extraction module.
Handles URL extraction and caption cleaning from text.
"""
import re
from typing import List, Dict, Optional


class LinkExtractor:
    """Extract and process links from text content."""
    
    # URL pattern matching http/https URLs
    URL_PATTERN = re.compile(r'https?://[^\s<>"\'()]+')
    
    def __init__(self):
        """Initialize link extractor."""
        pass
    
    def extract_links(self, text: Optional[str]) -> List[Dict[str, str]]:
        """Extract URLs and their descriptions from text.
        
        Args:
            text: Text containing URLs
            
        Returns:
            List of dictionaries with 'url' and 'description' keys
            
        Example:
            >>> extractor = LinkExtractor()
            >>> text = "Check this out https://example.com great stuff"
            >>> links = extractor.extract_links(text)
            >>> print(links[0])
            {'url': 'https://example.com', 'description': 'Check this out'}
        """
        if not text:
            return []
        
        urls = self.URL_PATTERN.findall(text)
        links = []
        
        for url in urls:
            # Get text before and after URL for context
            before = text.split(url)[0].split('\n')[-1].strip()
            after = text.split(url)[-1].split('\n')[0].strip()
            
            # Use the longer context as description
            description = before if len(before) > len(after) else after
            
            links.append({
                'url': url,
                'description': description
            })
        
        return links
    
    def determine_source_type(self, url: str) -> str:
        """Determine the platform/source type from URL.
        
        Args:
            url: The URL to analyze
            
        Returns:
            Platform name: 'LinkedIn', 'X', or 'Other'
        """
        if not url:
            return 'Other'
        
        url_lower = url.lower()
        
        if 'linkedin.com' in url_lower:
            return 'LinkedIn'
        elif any(domain in url_lower for domain in ['twitter.com', 'x.com']):
            return 'X'
        else:
            return 'Other'
    
    def clean_caption(self, text: Optional[str]) -> Optional[str]:
        """Clean caption text by removing markdown links and extra whitespace.
        
        Args:
            text: Raw caption text
            
        Returns:
            Cleaned text or None if empty
        """
        if not text:
            return None
        
        s = text
        
        # Remove markdown-style links [text](url)
        s = re.sub(r'\[.*?\]\([^\)]+\)', '', s)
        
        # Remove standalone URLs
        s = self.URL_PATTERN.sub('', s)
        
        # Remove common separators and channel mentions
        s = re.sub(r'———.*|⸻.*|⚜️@[\w]+', '', s)
        
        # Normalize whitespace
        s = re.sub(r'\n\s*\n+', '\n', s)
        s = s.strip()
        
        # Split by lines or separators and take longest part
        parts = [
            p.strip() 
            for p in re.split(r'\n|-{2,}', s) 
            if p.strip()
        ]
        
        if parts:
            # Return the longest meaningful part
            parts_sorted = sorted(parts, key=lambda p: len(p), reverse=True)
            return parts_sorted[0]
        
        return s if s else None
    
    def split_album_caption(self, text: Optional[str]) -> List[str]:
        """Split album caption into parts for multiple images.
        
        Args:
            text: Full caption text
            
        Returns:
            List of caption parts
        """
        if not text:
            return [""]
        
        # Split by link emoji or double newlines
        parts = [
            p.strip() 
            for p in re.split(r"🔗|\n{2,}", text) 
            if p.strip()
        ]
        
        return parts if parts else [text.strip()]
    
    def extract_username_from_url(
        self, 
        url: str, 
        platform: Optional[str] = None
    ) -> Optional[str]:
        """Extract username or company name from social media URLs.
        
        Args:
            url: Social media URL
            platform: Platform hint ('LinkedIn', 'X', etc.)
            
        Returns:
            Extracted username in readable format, or None
        """
        if not url:
            return None
        
        url_lower = url.lower()
        
        # LinkedIn patterns
        if "linkedin.com" in url_lower:
            # Profile: linkedin.com/in/username
            match = re.search(
                r"linkedin\.com/(?:in|company|school)/([^/?#]+)", 
                url_lower
            )
            if match:
                name = match.group(1)
                name = re.sub(r'[-_]', ' ', name)
                return name.title().strip()
            
            # Post: linkedin.com/posts/username_
            match = re.search(
                r"linkedin\.com/posts/([a-z0-9._-]+)_", 
                url_lower
            )
            if match:
                name = match.group(1)
                name = re.sub(r'[-_]', ' ', name)
                return name.title().strip()
        
        # X/Twitter patterns
        if any(domain in url_lower for domain in ("twitter.com", "x.com")):
            match = re.search(
                r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)/?", 
                url
            )
            if match:
                username = match.group(1).strip("@")
                return username.title()
        
        return None
    
    def is_valid_url(self, url: str) -> bool:
        """Check if string is a valid URL.
        
        Args:
            url: String to validate
            
        Returns:
            True if valid URL, False otherwise
        """
        if not url:
            return False
        
        return bool(self.URL_PATTERN.match(url))
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing tracking parameters.
        
        Args:
            url: URL to normalize
            
        Returns:
            Cleaned URL
        """
        if not url:
            return url
        
        # Remove common tracking parameters
        tracking_params = [
            'utm_source', 'utm_medium', 'utm_campaign',
            'utm_term', 'utm_content', 'fbclid', 'gclid'
        ]
        
        for param in tracking_params:
            url = re.sub(f'[?&]{param}=[^&]*', '', url)
        
        # Clean up URL
        url = url.rstrip('?&')
        
        return url