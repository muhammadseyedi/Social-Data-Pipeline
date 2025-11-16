"""
Telegram scraper module.
Handles both batch fetching and real-time message listening.
"""
import logging
import os
from typing import Optional, List
from pathlib import Path

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from ..config import Config
from ..database.connection import DatabaseManager
from ..extractors.link_extractor import LinkExtractor

logger = logging.getLogger(__name__)


class TelegramScraper:
    """Scraper for Telegram channels with batch and real-time capabilities."""
    
    def __init__(
        self, 
        config: Config = Config,
        db: Optional[DatabaseManager] = None
    ):
        """Initialize Telegram scraper.
        
        Args:
            config: Configuration object
            db: Database manager instance
        """
        self.config = config
        self.db = db or DatabaseManager(config)
        self.link_extractor = LinkExtractor()
        
        # Validate Telegram configuration
        if not config.TG_API_ID or not config.TG_API_HASH:
            raise ValueError("Telegram API credentials not configured")
        
        self.client = None
    
    async def connect(self) -> TelegramClient:
        """Connect to Telegram and return client."""
        if self.client and self.client.is_connected():
            return self.client
        
        session = StringSession(self.config.TG_SESSION_STR)
        self.client = TelegramClient(
            session, 
            self.config.TG_API_ID, 
            self.config.TG_API_HASH
        )
        
        await self.client.start()
        logger.info("✅ Connected to Telegram")
        return self.client
    
    async def disconnect(self):
        """Disconnect from Telegram."""
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from Telegram")
    
    async def download_media(
        self, 
        message, 
        dest_dir: Optional[Path] = None
    ) -> Optional[str]:
        """Download media from message.
        
        Args:
            message: Telegram message object
            dest_dir: Destination directory (default: MEDIA_DIR)
            
        Returns:
            Absolute path to downloaded file, or None if failed
        """
        if not dest_dir:
            dest_dir = self.config.MEDIA_DIR
        
        try:
            file_path = await message.download_media(file=str(dest_dir))
            if file_path:
                return os.path.abspath(file_path)
        except Exception as e:
            logger.warning(f"Media download failed: {e}")
        
        return None
    
    def _extract_caption(self, message) -> str:
        """Extract caption text from message."""
        return (
            getattr(message, 'text', None) or 
            getattr(message, 'message', "") or 
            ""
        )
    
    async def save_single_message(
        self, 
        message, 
        channel_username: Optional[str] = None
    ):
        """Save a single message to database.
        
        Args:
            message: Telegram message object
            channel_username: Channel username (default: from config)
        """
        channel = channel_username or self.config.TG_CHANNEL_USERNAME
        
        with self.db.get_cursor() as (cur, conn):
            # Check if post already exists
            cur.execute(
                "SELECT COUNT(*) FROM dbo.Posts WHERE telegram_message_id = ?",
                (message.id,)
            )
            if cur.fetchone()[0]:
                logger.debug(f"Post {message.id} already exists")
                return
            
            # Insert post
            cur.execute("""
                INSERT INTO dbo.Posts 
                (telegram_message_id, telegram_date, source_channel, source_type)
                VALUES (?, ?, ?, ?)
            """, (message.id, message.date, channel, "Telegram"))
            
            # Extract caption and links
            caption_raw = self._extract_caption(message)
            caption_clean = self.link_extractor.clean_caption(caption_raw)
            links = self.link_extractor.extract_links(caption_raw)
            
            # Download media if present
            image_path = None
            if getattr(message, 'media', None):
                image_path = await self.download_media(message)
            
            # Check for duplicate media
            if image_path:
                cur.execute(
                    "SELECT COUNT(*) FROM dbo.MediaItems WHERE image_path = ?",
                    (image_path,)
                )
                if cur.fetchone()[0]:
                    logger.debug(f"Media already exists: {image_path}")
                    return
            
            # Insert media item
            cur.execute("""
                INSERT INTO dbo.MediaItems 
                (telegram_message_id, part_number, caption, image_path)
                VALUES (?, ?, ?, ?)
            """, (message.id, 1, caption_clean, image_path))
            
            media_id = self.db.get_last_insert_id(cur)
            
            # Insert links
            for link in links:
                url = link.get('url')
                if not url:
                    continue
                
                cur.execute(
                    "SELECT COUNT(*) FROM dbo.Links WHERE link_url = ? AND media_id = ?",
                    (url, media_id)
                )
                
                if not cur.fetchone()[0]:
                    desc = (
                        self.link_extractor.clean_caption(link.get('description', '')) 
                        or caption_clean 
                        or ""
                    )
                    source_type = self.link_extractor.determine_source_type(url)
                    
                    cur.execute("""
                        INSERT INTO dbo.Links 
                        (media_id, link_url, link_description, Source_Type)
                        VALUES (?, ?, ?, ?)
                    """, (media_id, url, desc, source_type))
            
            conn.commit()
            logger.info(f"✅ Saved message {message.id} (media_id={media_id})")
    
    async def save_album_messages(
        self,
        messages: List,
        channel_username: Optional[str] = None
    ):
        """Save album (grouped messages) to database.
        
        Args:
            messages: List of grouped Telegram messages
            channel_username: Channel username
        """
        if not messages:
            return
        
        channel = channel_username or self.config.TG_CHANNEL_USERNAME
        
        # Find message with caption or use first
        caption_msg = next(
            (m for m in messages if self._extract_caption(m)),
            messages[0]
        )
        
        # Sort by ID
        messages = sorted(messages, key=lambda m: m.id)
        first_msg = messages[0]
        
        with self.db.get_cursor() as (cur, conn):
            # Check if album already exists
            cur.execute(
                "SELECT COUNT(*) FROM dbo.Posts WHERE telegram_message_id = ?",
                (first_msg.id,)
            )
            if cur.fetchone()[0]:
                logger.info(f"⚠️ Album {first_msg.id} already exists")
                return
            
            # Insert post
            cur.execute("""
                INSERT INTO dbo.Posts 
                (telegram_message_id, telegram_date, source_channel, source_type)
                VALUES (?, ?, ?, ?)
            """, (first_msg.id, first_msg.date, channel, "Telegram"))
            
            post_id = first_msg.id
            
            # Extract full caption and split by parts
            full_caption = self._extract_caption(caption_msg)
            parts = self.link_extractor.split_album_caption(full_caption)
            
            # Process each message in album
            for i, msg in enumerate(messages, start=1):
                caption_part = parts[i - 1] if i - 1 < len(parts) else parts[-1]
                caption_clean = self.link_extractor.clean_caption(caption_part)
                links = self.link_extractor.extract_links(caption_part)
                
                # Download media
                image_path = None
                if getattr(msg, 'media', None):
                    image_path = await self.download_media(msg)
                
                # Check duplicate media
                if image_path:
                    cur.execute(
                        "SELECT COUNT(*) FROM dbo.MediaItems WHERE image_path = ?",
                        (image_path,)
                    )
                    if cur.fetchone()[0]:
                        logger.info(f"⚠️ Media exists: {image_path}")
                        continue
                
                # OCR if available
                ocr_text = None
                if image_path and os.path.exists(image_path):
                    try:
                        from PIL import Image
                        import pytesseract
                        
                        ocr_text = pytesseract.image_to_string(
                            Image.open(image_path)
                        ).strip()
                    except Exception as e:
                        logger.warning(f"OCR failed: {e}")
                
                # Insert media item
                cur.execute("""
                    INSERT INTO dbo.MediaItems 
                    (post_id, telegram_message_id, part_number, caption, image_path, ocr_text)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (post_id, caption_msg.id, i, caption_clean, image_path, ocr_text))
                
                media_id = self.db.get_last_insert_id(cur)
                
                # Insert links
                for link in links:
                    url = link.get('url')
                    if not url:
                        continue
                    
                    cur.execute(
                        "SELECT COUNT(*) FROM dbo.Links WHERE link_url = ? AND media_id = ?",
                        (url, media_id)
                    )
                    
                    if not cur.fetchone()[0]:
                        desc = (
                            self.link_extractor.clean_caption(link.get('description', ''))
                            or caption_clean
                            or ""
                        )
                        source_type = self.link_extractor.determine_source_type(url)
                        
                        cur.execute("""
                            INSERT INTO dbo.Links 
                            (media_id, link_url, link_description, Source_Type)
                            VALUES (?, ?, ?, ?)
                        """, (media_id, url, desc, source_type))
                
                logger.info(f"🖼️ Saved album part {i}/{len(messages)}")
            
            conn.commit()
            logger.info(f"✅ Album {post_id} saved with {len(messages)} items")
    
    async def fetch_batch(
        self, 
        limit: int = 50,
        channel_username: Optional[str] = None
    ):
        """Fetch messages in batch mode.
        
        Args:
            limit: Maximum number of messages to fetch
            channel_username: Channel username (default: from config)
        """
        channel = channel_username or self.config.TG_CHANNEL_USERNAME
        client = await self.connect()
        
        logger.info(f"📥 Fetching up to {limit} messages from {channel}")
        
        album_msgs = []
        current_group_id = None
        
        async for msg in client.iter_messages(channel, limit=limit):
            try:
                gid = getattr(msg, 'grouped_id', None)
                
                if gid:
                    # Handle grouped messages (album)
                    if current_group_id and gid != current_group_id and album_msgs:
                        await self.save_album_messages(album_msgs, channel)
                        album_msgs = []
                    
                    album_msgs.append(msg)
                    current_group_id = gid
                else:
                    # Save pending album first
                    if album_msgs:
                        await self.save_album_messages(album_msgs, channel)
                        album_msgs = []
                        current_group_id = None
                    
                    # Save single message
                    await self.save_single_message(msg, channel)
            
            except Exception as e:
                logger.exception(f"❌ Error processing message {getattr(msg, 'id', '?')}: {e}")
        
        # Save any remaining album
        if album_msgs:
            await self.save_album_messages(album_msgs, channel)
        
        logger.info("✅ Batch fetch completed")
    
    async def listen_realtime(
        self,
        channel_username: Optional[str] = None
    ):
        """Start real-time message listener.
        
        Args:
            channel_username: Channel username (default: from config)
        """
        channel = channel_username or self.config.TG_CHANNEL_USERNAME
        client = await self.connect()
        
        @client.on(events.NewMessage(chats=channel))
        async def handler(event):
            msg = event.message
            logger.info(f"📨 New message received: {msg.id}")
            
            try:
                await self.save_single_message(msg, channel)
            except Exception:
                logger.exception("Error handling new message")
        
        logger.info(f"👂 Listening for new messages in {channel}")
        
        try:
            await client.run_until_disconnected()
        finally:
            logger.info("Real-time listener stopped")