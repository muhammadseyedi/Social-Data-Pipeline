"""
Job information extraction module.
Extracts structured job posting data from text.
"""
import logging
import re
from typing import Dict, Optional, List

from ..database.connection import DatabaseManager
from ..processors.nlp_processor import NLPProcessor
from ..utils.date_parser import DateParser

logger = logging.getLogger(__name__)


class JobExtractor:
    """Extract job posting information from social media content."""
    
    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        nlp: Optional[NLPProcessor] = None
    ):
        """Initialize job extractor.
        
        Args:
            db: Database manager instance
            nlp: NLP processor instance (optional, loaded on demand)
        """
        self.db = db or DatabaseManager()
        self.nlp = nlp  # Don't load by default
        self.date_parser = DateParser()
    
    def populate_from_social_extracts(self, limit: Optional[int] = None) -> int:
        """Populate JobPosts table from SocialExtracts.
        
        Args:
            limit: Maximum number of records to process
            
        Returns:
            Number of job posts created
        """
        logger.info("Populating JobPosts from SocialExtracts...")
        
        with self.db.get_cursor() as (cur, conn):
            # Query social extracts
            query = """
                SELECT s.Id AS sx_id, s.link_id, s.Username, s.PostDate,
                       s.PostContent, s.Platform, s.OriginalLink,
                       l.link_description,
                       m.post_id AS media_post_id, p.telegram_date
                FROM dbo.SocialExtracts s
                LEFT JOIN dbo.Links l ON s.link_id = l.id
                LEFT JOIN dbo.MediaItems m ON l.media_id = m.id
                LEFT JOIN dbo.Posts p ON m.post_id = p.telegram_message_id
            """
            
            if limit:
                query += f" ORDER BY s.Id DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
            
            cur.execute(query)
            rows = cur.fetchall()
            
            inserted = 0
            skipped_no_date = 0
            skipped_duplicate = 0
            
            for row in rows:
                # Parse date
                raw_date = getattr(row, "PostDate", None)
                post_date = self.date_parser.parse(raw_date)
                
                if not post_date:
                    skipped_no_date += 1
                    logger.debug(f"Skipping sx_id={getattr(row, 'sx_id', None)} (no valid date)")
                    continue
                
                link_id = getattr(row, "link_id", None)
                
                # Check for duplicates
                if link_id:
                    cur.execute(
                        "SELECT COUNT(*) FROM dbo.JobPosts WHERE LinkId = ?",
                        (link_id,)
                    )
                    if cur.fetchone()[0]:
                        skipped_duplicate += 1
                        continue
                
                # Fallback: check by original link
                orig_link = getattr(row, "OriginalLink", None)
                if orig_link:
                    cur.execute(
                        "SELECT COUNT(*) FROM dbo.JobPosts WHERE Links = ?",
                        (orig_link,)
                    )
                    if cur.fetchone()[0]:
                        skipped_duplicate += 1
                        continue
                
                # Prepare job data
                description = (
                    getattr(row, "PostContent", None) or
                    getattr(row, "link_description", None) or
                    ""
                ).strip()
                
                # Extract title from first sentence
                title = None
                if description:
                    first_sentence = re.split(r'\n|\.|\!|\?', description, maxsplit=1)[0]
                    title = first_sentence[:250].strip()
                
                # Insert job post
                cur.execute("""
                    INSERT INTO dbo.JobPosts (
                        PostId, LinkId, Title, Employer, University, Location,
                        JobPublishedDate, TelegramMessageDate, JobType,
                        Field, ResearchTopic, Description, SourceType,
                        Links, IsIncomplete
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    getattr(row, "media_post_id", None),
                    link_id,
                    title,
                    getattr(row, "Username", None),  # Employer
                    None,  # University (filled by NLP)
                    None,  # Location (filled by NLP)
                    post_date,
                    getattr(row, "telegram_date", None),
                    None,  # JobType (filled by NLP)
                    None,  # Field (filled by NLP)
                    None,  # ResearchTopic (filled by NLP)
                    description,
                    getattr(row, "Platform", None),
                    orig_link
                ))
                
                inserted += 1
            
            conn.commit()
        
        logger.info(
            f"✅ populate_jobs completed: inserted={inserted}, "
            f"skipped_no_date={skipped_no_date}, skipped_duplicate={skipped_duplicate}"
        )
        
        return inserted
    
    def process_nlp_extraction(self, limit: int = 200, dry_run: bool = False) -> Dict:
        """Run NLP extraction on JobPosts.
        
        Args:
            limit: Maximum number of posts to process
            dry_run: If True, don't save to database
            
        Returns:
            Dictionary with update statistics
        """
        logger.info(f"Processing {limit} JobPosts with NLP extraction...")
        
        with self.db.get_cursor() as (cur, conn):
            # Get job posts with content
            cur.execute(f"""
                SELECT TOP {limit}
                    j.Id AS job_id,
                    j.Title,
                    j.Description,
                    j.LinkId,
                    l.link_description,
                    m.ocr_text
                FROM dbo.JobPosts j
                LEFT JOIN dbo.Links l ON j.LinkId = l.id
                LEFT JOIN dbo.MediaItems m ON l.media_id = m.id
                WHERE j.Title IS NOT NULL OR j.Description IS NOT NULL OR m.ocr_text IS NOT NULL
                ORDER BY j.Id DESC
            """)
            
            rows = cur.fetchall()
            logger.info(f"Found {len(rows)} job posts to process")
            
            if not rows:
                return {"updated": 0, "preview_count": 0}
            
            # Prepare texts for batch processing
            texts = []
            job_ids = []
            
            for row in rows:
                title = getattr(row, "Title", None) or ""
                desc = getattr(row, "Description", None) or ""
                link_desc = getattr(row, "link_description", None) or ""
                ocr_text = getattr(row, "ocr_text", None) or ""
                
                # Clean OCR text
                ocr_clean = re.sub(r"[^A-Za-z0-9\s#@.,:/\-]", " ", ocr_text)
                ocr_clean = re.sub(r"\s+", " ", ocr_clean).strip()
                
                # Combine all text
                combined = " ".join(filter(None, [
                    title.strip(),
                    desc.strip(),
                    link_desc.strip(),
                    ocr_clean
                ]))
                
                texts.append(combined)
                job_ids.append(getattr(row, "job_id"))
            
            # Process with NLP
            batch_updates = []
            results_preview = []
            
            for text, job_id in zip(texts, job_ids):
                if not text.strip():
                    continue
                
                try:
                    # Extract entities
                    entities = self.nlp.extract_entities(text)
                    
                    if not any(entities.values()):
                        continue
                    
                    # Preview
                    preview = {
                        "Id": job_id,
                        "University": entities.get("University"),
                        "Location": entities.get("Location"),
                        "Field": entities.get("Field"),
                        "ResearchTopic": entities.get("ResearchTopic"),
                        "JobType": entities.get("JobType"),
                        "sample_text": text[:200] + "..." if len(text) > 200 else text
                    }
                    results_preview.append(preview)
                    
                    if not dry_run:
                        batch_updates.append((
                            entities.get("University"),
                            entities.get("Location"),
                            entities.get("Field"),
                            entities.get("ResearchTopic"),
                            entities.get("JobType"),
                            job_id
                        ))
                
                except Exception as e:
                    logger.warning(f"Error processing job_id={job_id}: {e}")
            
            # Save to database
            updated_count = 0
            if not dry_run and batch_updates:
                update_query = """
                    UPDATE dbo.JobPosts
                    SET University = ?,
                        Location = ?,
                        Field = ?,
                        ResearchTopic = ?,
                        JobType = ?
                    WHERE Id = ?
                """
                cur.executemany(update_query, batch_updates)
                conn.commit()
                updated_count = len(batch_updates)
        
        logger.info(
            f"✅ NLP extraction complete: updated={updated_count}, "
            f"preview={len(results_preview)}"
        )
        
        return {
            "updated": updated_count,
            "preview_count": len(results_preview),
            "preview": results_preview[:10]  # First 10 for preview
        }
    
    def extract_from_text(self, text: str) -> Dict[str, Optional[str]]:
        """Extract job information from raw text.
        
        Args:
            text: Text containing job information
            
        Returns:
            Dictionary with extracted job information
        """
        return self.nlp.extract_entities(text)