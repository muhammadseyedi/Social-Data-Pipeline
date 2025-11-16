"""
X (Twitter) scraper module.
Handles scraping posts from X/Twitter using Selenium.
"""
import logging
import time
from typing import Dict, Optional
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from ..config import Config

logger = logging.getLogger(__name__)


class XScraper:
    """Scraper for X (Twitter) posts."""
    
    def __init__(self, config: Config = Config, headless: bool = None):
        """Initialize X scraper.
        
        Args:
            config: Configuration object
            headless: Run browser in headless mode (default: from config)
        """
        self.config = config
        self.headless = headless if headless is not None else config.SELENIUM_HEADLESS
        self.driver = None
    
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
        
        # Anti-detection options
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
        
        # Additional anti-detection
        try:
            driver.execute_cdp_cmd(
                'Network.setUserAgentOverride',
                {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception as e:
            logger.warning(f"Could not set anti-detection properties: {e}")
        
        driver.set_page_load_timeout(timeout)
        self.driver = driver
        return driver
    
    def scrape_post(self, url: str, wait_time: int = 12) -> Dict[str, Optional[str]]:
        """Scrape a single X post.
        
        Args:
            url: URL of the X post
            wait_time: Maximum wait time for elements
            
        Returns:
            Dictionary with keys:
                - Username: Post author username
                - PostDate: Publication date/time
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
            logger.info(f"🔗 Scraping X post: {url}")
            self.driver.get(url)
            time.sleep(1.2)
            
            # Scroll to load content
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(0.25)
            
            # Wait for article element
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, 'article'))
            )
            
            # Extract username
            try:
                username_elem = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "article a[role='link'] span"
                )
                data['Username'] = username_elem.text.strip()
                logger.debug(f"Found username: {data['Username']}")
            except Exception as e:
                logger.warning(f"Could not extract username: {e}")
            
            # Extract post date
            try:
                time_elem = self.driver.find_element(By.XPATH, "//time")
                data['PostDate'] = (
                    time_elem.get_attribute('datetime') or 
                    time_elem.text
                )
                logger.debug(f"Found date: {data['PostDate']}")
            except Exception as e:
                logger.warning(f"Could not extract date: {e}")
            
            # Extract post content
            try:
                # Try to get all text parts with lang attribute
                content_parts = self.driver.find_elements(
                    By.XPATH,
                    "//article//div[@lang]/*"
                )
                
                text_parts = []
                for elem in content_parts:
                    txt = elem.text.strip()
                    if not txt:
                        continue
                    
                    tag = elem.tag_name.lower()
                    
                    # Add link if it's an anchor tag
                    if tag == 'a':
                        href = elem.get_attribute('href')
                        if href and not any(x in href for x in ['status', 'twitter.com', 'x.com']):
                            txt = f"{txt} ({href})"
                    
                    text_parts.append(txt)
                
                if text_parts:
                    data['PostContent'] = " ".join(text_parts)
                else:
                    # Fallback: get entire content div
                    content_div = self.driver.find_element(
                        By.CSS_SELECTOR,
                        "article div[lang]"
                    )
                    data['PostContent'] = content_div.text.strip()
                
                logger.debug(f"Content length: {len(data['PostContent']) if data['PostContent'] else 0}")
                
            except Exception as e:
                logger.warning(f"Could not extract content: {e}")
                data['PostContent'] = None
            
            logger.info(f"✅ Successfully scraped X post")
            
        except Exception as e:
            logger.error(f"❌ Failed to scrape X post {url}: {e}")
        
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
    
    def __enter__(self):
        """Context manager entry."""
        self.init_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()