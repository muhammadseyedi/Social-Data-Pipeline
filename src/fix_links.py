"""
Fix link descriptions from MediaItems captions
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database.connection import DatabaseManager
from src.extractors.link_extractor import LinkExtractor

def fix_link_descriptions():
    """Fix link descriptions."""
    
    print("🔗 Fixing Link Descriptions...")
    
    db = DatabaseManager()
    extractor = LinkExtractor()
    
    with db.get_cursor() as (cur, conn):
        # Get all links with media
        cur.execute("""
            SELECT L.id, L.link_description, M.caption, M.ocr_text
            FROM dbo.Links L
            INNER JOIN dbo.MediaItems M ON L.media_id = M.id
            WHERE L.media_id IS NOT NULL
        """)
        
        rows = cur.fetchall()
        
        if not rows:
            print("ℹ️  No links to fix")
            return
        
        print(f"Processing {len(rows)} links...")
        fixed = 0
        
        for row in rows:
            link_id = row.id
            old_desc = row.link_description or ""
            caption = row.caption or ""
            ocr_text = row.ocr_text or ""
            
            # Combine caption and OCR
            combined = f"{caption}\n{ocr_text}".strip()
            
            # Clean description
            new_desc = extractor.clean_caption(combined)
            
            # Update if changed
            if new_desc and new_desc != old_desc:
                cur.execute("""
                    UPDATE dbo.Links 
                    SET link_description = ? 
                    WHERE id = ?
                """, (new_desc, link_id))
                fixed += 1
                
                if fixed % 10 == 0:
                    conn.commit()
                    print(f"   Fixed {fixed}...")
        
        conn.commit()
        print(f"✅ Fixed {fixed}/{len(rows)} link descriptions")

if __name__ == "__main__":
    try:
        fix_link_descriptions()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()