"""
LinkedIn scraper module.
Handles scraping posts from LinkedIn using Selenium.
"""
import logging
import time
import re
from typing import Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from ..config import Config

logger = logging.getLogger(__name__)


class LinkedInScraper:
    """Scraper for LinkedIn posts."""
    
    def __init__(self, config: Config = Config, headless: bool = None):
        """Initialize LinkedIn scraper.
        
        Args:
            config: Configuration object
            headless: Run browser in headless mode (default: from config)
        """
        self.config = config
        self.headless = headless if headless is not None else config.SELENIUM_HEADLESS
        self.driver = None
        self.logged_in = False
    
    def init_driver(self, timeout: int = 60) -> webdriver.Chrome:
        """Initialize Selenium WebDriver.
        
        Args:
            timeout: Page load timeout in seconds
            
        Returns:
            Configured Chrome WebDriver instance
        """
        opts = Options()
        
        if self.headless:
            opts.add_argument("--headless=new")
        
        # Standard options
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1200,900")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        
        # Anti-detection
        try:
            driver.execute_cdp_cmd(
                'Network.setUserAgentOverride',
                {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception as e:
            logger.warning(f"Could not set anti-detection: {e}")
        
        driver.set_page_load_timeout(timeout)
        self.driver = driver
        return driver
    
    def login(self, email: str = None, password: str = None, wait_time: int = 20) -> bool:
        """Login to LinkedIn.
        
        Args:
            email: LinkedIn email (default: from config)
            password: LinkedIn password (default: from config)
            wait_time: Maximum wait time for login
            
        Returns:
            True if login successful, False otherwise
        """
        if self.logged_in:
            logger.info("Already logged in")
            return True
        
        if not self.driver:
            self.init_driver()
        
        email = email or self.config.LINKEDIN_EMAIL
        password = password or self.config.LINKEDIN_PASSWORD
        
        if not email or not password:
            logger.warning("LinkedIn credentials not provided")
            return False
        
        try:
            logger.info("🔐 Logging into LinkedIn...")
            self.driver.get("https://www.linkedin.com/login")
            
            # Wait for login form
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            
            # Enter credentials
            username_field = self.driver.find_element(By.ID, "username")
            password_field = self.driver.find_element(By.ID, "password")
            
            username_field.send_keys(email)
            password_field.send_keys(password)
            password_field.submit()
            
            # Wait for dashboard
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.ID, "global-nav-search"))
            )
            
            self.logged_in = True
            logger.info("✅ Successfully logged into LinkedIn")
            return True
            
        except Exception as e:
            logger.error(f"❌ LinkedIn login failed: {e}")
            return False
    
    def clean_content(
        self, 
        raw_text: Optional[str], 
        username_hint: Optional[str] = None
    ) -> Optional[str]:
        """Clean LinkedIn content by removing UI noise.
        
        Args:
            raw_text: Raw scraped text
            username_hint: Username to filter out
            
        Returns:
            Cleaned text
        """
        if not raw_text:
            return None
        
        text = raw_text
        
        # Noise patterns to remove
        noise_patterns = [
            r'Feed post', r'Follow', r'Your document has finished loading',
            r'Reactions', r'Add a comment', r'Open Emoji Keyboard',
            r'Current selected sort order is .*', r'Edited',
            r'• \d+ (replies|comments|reposts|reactions)'
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.I)
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
        
        # Filter paragraphs
        filtered = []
        for para in paragraphs:
            # Remove username lines if they're short
            if username_hint and username_hint.lower() in para.lower() and len(para.split()) < 6:
                continue
            
            # Keep short paragraphs only if they contain links or hashtags
            if len(para) < 30:
                if re.search(r'apply|application|https?://|#', para, re.I):
                    filtered.append(para)
                else:
                    continue
            else:
                filtered.append(para)
        
        # If nothing left, take longest paragraph
        if not filtered and paragraphs:
            paragraphs_sorted = sorted(paragraphs, key=lambda x: len(x), reverse=True)
            return paragraphs_sorted[0]
        
        # Remove duplicates while preserving order
        unique = []
        for para in filtered:
            if not unique or para != unique[-1]:
                unique.append(para)
        
        return "\n\n".join(unique) if unique else None
    
    def scrape_post(self, url: str, wait_time: int = 14) -> Dict[str, Optional[str]]:
        """Scrape a single LinkedIn post.
        
        Args:
            url: URL of the LinkedIn post
            wait_time: Maximum wait time for elements
            
        Returns:
            Dictionary with keys:
                - Username: Post author name/company
                - PostDate: Publication date
                - PostContent: Post text content
        """
        data = {
            'Username': None,
            'PostDate': None,
            'PostContent': None
        }
        
        if not self.driver:
            self.init_driver()
        
        try:
            logger.info(f"🔗 Scraping LinkedIn post: {url}")
            self.driver.get(url)
            time.sleep(1.2)
            
            # Scroll to load content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(0.8)
            
            # Extract username/company
            try:
                username_elem = self.driver.find_element(
                    By.XPATH,
                    "//span[contains(@class,'feed-shared-actor__name') or "
                    "contains(@class,'update-components-actor__name')]"
                )
                data['Username'] = username_elem.text.strip()
                logger.debug(f"Found username: {data['Username']}")
            except Exception:
                try:
                    # Fallback: look for profile link
                    link_elem = self.driver.find_element(
                        By.XPATH,
                        "//a[contains(@href,'/in/') or contains(@href,'/company/') or "
                        "contains(@href,'/posts/')]"
                    )
                    data['Username'] = link_elem.text.strip()
                except Exception as e:
                    logger.warning(f"Could not extract username: {e}")
            
            # Extract post date
            try:
                # Try time element first
                time_elem = self.driver.find_element(By.XPATH, "//time")
                data['PostDate'] = (
                    time_elem.text.strip() or 
                    time_elem.get_attribute('datetime')
                )
                logger.debug(f"Found date: {data['PostDate']}")
            except Exception:
                try:
                    # Fallback: subtitle with date
                    date_elem = self.driver.find_element(
                        By.XPATH,
                        "//span[contains(@class,'update-components-actor__sub-description') or "
                        "contains(@class,'feed-shared-actor__sub-description')]"
                    )
                    data['PostDate'] = date_elem.text.strip()
                except Exception as e:
                    logger.warning(f"Could not extract date: {e}")
            
            # Extract post content
            try:
                content_div = None
                
                # Try main content div
                try:
                    content_div = self.driver.find_element(
                        By.XPATH,
                        "//div[contains(@class,'feed-shared-update-v2__description') or "
                        "contains(@class,'update-components-text') or "
                        "contains(@class,'feed-shared-text-view')]"
                    )
                except Exception:
                    # Fallback: article tag
                    try:
                        content_div = self.driver.find_element(By.CSS_SELECTOR, "article")
                    except Exception:
                        pass
                
                if content_div:
                    # Extract text nodes and links
                    nodes = content_div.find_elements(By.XPATH, ".//a | .//span | .//p")
                    parts = []
                    
                    for node in nodes:
                        txt = node.text.strip()
                        if not txt:
                            continue
                        
                        tag = node.tag_name.lower()
                        
                        # Add href for external links
                        if tag == 'a':
                            href = node.get_attribute('href')
                            if href and 'linkedin.com' not in href:
                                txt = f"{txt} ({href})"
                        
                        parts.append(txt)
                    
                    raw_content = " ".join(parts) if parts else None
                else:
                    # Last resort: get article text
                    try:
                        raw_content = self.driver.find_element(
                            By.CSS_SELECTOR, 
                            "article"
                        ).text
                    except Exception:
                        raw_content = None
                
                # Clean the content
                username_hint = data.get('Username')
                data['PostContent'] = self.clean_content(raw_content, username_hint)
                
                logger.debug(f"Content length: {len(data['PostContent']) if data['PostContent'] else 0}")
                
            except Exception as e:
                logger.warning(f"Could not extract content: {e}")
            
            logger.info(f"✅ Successfully scraped LinkedIn post")
            
        except Exception as e:
            logger.error(f"❌ Failed to scrape LinkedIn post {url}: {e}")
        
        return data
    
    def close(self):
        """Close the browser driver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.driver = None
                self.logged_in = False
    
    def __enter__(self):
        """Context manager entry."""
        self.init_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()