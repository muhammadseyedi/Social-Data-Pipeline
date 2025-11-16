"""
Run complete pipeline from start to finish.
"""
import sys
import subprocess
from pathlib import Path

def run_command(cmd: list) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*70}")
    print(f"Running: {' '.join(cmd)}")
    print('='*70)
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run full pipeline."""
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🚀 Full Pipeline Execution                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("This will run the complete pipeline:")
    print("  1️⃣  Setup database")
    print("  2️⃣  Fetch Telegram messages (50)")
    print("  3️⃣  Run OCR on images")
    print("  4️⃣  Scrape social media links")
    print("  5️⃣  Process and translate")
    print("  6️⃣  Populate job posts")
    print("  7️⃣  Extract entities with NLP")
    print()
    
    confirm = input("❓ Continue? (yes/no): ")
    if confirm.lower() not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    steps = [
        # 1. Database
        (["python", "-m", "src.cli", "db"], "Database setup"),
        
        # 2. Fetch Telegram
        (["python", "-m", "src.cli", "telegram", "50"], "Telegram fetch"),
        
        # 3. OCR
        (["python", "-m", "src.cli", "ocr"], "OCR processing"),
        
        # 4. Scrape
        (["python", "-m", "src.cli", "scrape-all"], "Social media scraping"),
        
        # 5. Process
        (["python", "-m", "src.cli", "process"], "Content processing"),
        
        # 6. Populate jobs
        (["python", "-m", "src.cli", "populate-jobs"], "Job population"),
        
        # 7. NLP
        (["python", "-m", "src.cli", "nlp", "200"], "NLP extraction"),
    ]
    
    failed_steps = []
    
    for i, (cmd, description) in enumerate(steps, 1):
        print(f"\n{'#'*70}")
        print(f"# Step {i}/{len(steps)}: {description}")
        print(f"{'#'*70}")
        
        if not run_command(cmd):
            failed_steps.append((i, description))
            
            continue_anyway = input(f"\n⚠️  Step failed. Continue anyway? (yes/no): ")
            if continue_anyway.lower() not in ['yes', 'y']:
                print("❌ Pipeline stopped")
                break
    
    # Summary
    print("\n" + "="*70)
    print("📊 PIPELINE SUMMARY")
    print("="*70)
    
    if failed_steps:
        print(f"\n⚠️  {len(failed_steps)} step(s) failed:")
        for step_num, description in failed_steps:
            print(f"   {step_num}. {description}")
    else:
        print("\n✅ All steps completed successfully!")
    
    # Show status
    print("\n" + "="*70)
    print("📈 Final Status:")
    print("="*70)
    run_command(["python", "-m", "src.cli", "status"])
    
    print("\n🎉 Pipeline execution finished!")
    print("\n💡 Next steps:")
    print("   - View data: python -m src.cli preview JobPosts 10")
    print("   - Run realtime: python -m src.cli realtime")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)