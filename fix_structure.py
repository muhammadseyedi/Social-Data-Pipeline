"""
Script to fix project structure by moving files into src/ directory.
Run this from your project root: D:\Projects\telegram-linkedin-X\
"""
import os
import shutil
from pathlib import Path


def fix_project_structure():
    """Move all Python modules into src/ directory."""
    
    print("🔧 Fixing project structure...\n")
    
    # Get current directory
    root = Path.cwd()
    print(f"📁 Working directory: {root}\n")
    
    # Create src directory if it doesn't exist
    src_dir = root / "src"
    src_dir.mkdir(exist_ok=True)
    print(f"✅ Created/verified: src/\n")
    
    # Directories to move into src/
    dirs_to_move = [
        'database',
        'scrapers', 
        'processors',
        'exteractors',  # Note: you have a typo, it's "exteractors" not "extractors"
        'utils'
    ]
    
    # Files to move into src/
    files_to_move = [
        'config.py',
        'cli.py',
        '__init__.py'
    ]
    
    # Move directories
    print("📦 Moving directories into src/...")
    for dir_name in dirs_to_move:
        source = root / dir_name
        target = src_dir / dir_name
        
        if source.exists() and source != target:
            if target.exists():
                print(f"  ℹ️  {dir_name}/ already in src/, skipping")
            else:
                shutil.move(str(source), str(target))
                print(f"  ✅ Moved: {dir_name}/ → src/{dir_name}/")
        elif not source.exists():
            print(f"  ⚠️  Not found: {dir_name}/")
    
    # Move files
    print("\n📄 Moving files into src/...")
    for file_name in files_to_move:
        source = root / file_name
        target = src_dir / file_name
        
        if source.exists() and source != target:
            if target.exists():
                print(f"  ℹ️  {file_name} already in src/, skipping")
            else:
                shutil.move(str(source), str(target))
                print(f"  ✅ Moved: {file_name} → src/{file_name}")
        elif not source.exists():
            print(f"  ⚠️  Not found: {file_name}")
    
    # Create __init__.py files in subdirectories
    print("\n📝 Creating __init__.py files...")
    subdirs = ['database', 'scrapers', 'processors', 'exteractors', 'utils']
    
    for subdir in subdirs:
        init_file = src_dir / subdir / '__init__.py'
        if not init_file.exists():
            init_file.touch()
            print(f"  ✅ Created: src/{subdir}/__init__.py")
        else:
            print(f"  ℹ️  Exists: src/{subdir}/__init__.py")
    
    # Update src/__init__.py
    src_init = src_dir / '__init__.py'
    src_init_content = '''"""
Social Data Pipeline - A comprehensive job scraping and analysis system.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .config import Config

__all__ = ["Config"]
'''
    src_init.write_text(src_init_content, encoding='utf-8')
    print(f"  ✅ Updated: src/__init__.py")
    
    # Note about typo
    if (src_dir / 'exteractors').exists():
        print("\n⚠️  IMPORTANT: You have a typo in folder name!")
        print("   'exteractors' should be 'extractors'")
        print("   Rename it manually or run:")
        print("   move src\\exteractors src\\extractors")
    
    print("\n" + "="*60)
    print("✅ Structure fixed successfully!")
    print("="*60)
    
    print("\n📋 Final structure:")
    print("src/")
    print("├── __init__.py")
    print("├── config.py")
    print("├── cli.py")
    print("├── database/")
    print("├── scrapers/")
    print("├── processors/")
    print("├── exteractors/  ⚠️  (rename to 'extractors')")
    print("└── utils/")
    
    print("\n🚀 Now you can run:")
    print("   python -m src.cli help")
    print("   python -m src.cli db")
    

if __name__ == "__main__":
    try:
        fix_project_structure()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()