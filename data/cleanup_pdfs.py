#!/usr/bin/env python3
import os
from pathlib import Path

BASE_DIR = Path("/Users/harish/Public/Govt")
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = BASE_DIR / "procesed_docs"

def cleanup():
    print("🧹 Starting cleanup of already processed PDF files...")
    
    # Scan all text files in processed directories to build a fast lookup set
    processed_stems = set()
    
    # 1. Gather stems from procesed_docs/
    for txt_path in PROCESSED_DIR.rglob("*.txt"):
        stem = txt_path.name
        # Remove suffix like _text.txt
        if stem.endswith("_text.txt"):
            stem = stem[:-9]
        elif stem.endswith(".txt"):
            stem = stem[:-4]
        processed_stems.add(stem.lower())
        
    # 2. Gather stems from data/exam_resources/
    for txt_path in DATA_DIR.rglob("*.txt"):
        stem = txt_path.name
        if stem.endswith("_text.txt"):
            stem = stem[:-9]
        elif stem.endswith(".txt"):
            stem = stem[:-4]
        processed_stems.add(stem.lower())
        
    print(f"Loaded {len(processed_stems)} processed document signatures.")
    
    total_space_saved = 0
    deleted_count = 0
    skipped_count = 0
    
    # Find and evaluate all PDFs in the data folder
    pdf_files = list(DATA_DIR.rglob("*.pdf"))
    
    for pdf_path in pdf_files:
        stem = pdf_path.stem.lower()
        size = pdf_path.stat().st_size
        
        # Check if the PDF has a corresponding processed text file
        if stem in processed_stems:
            try:
                os.remove(pdf_path)
                total_space_saved += size
                deleted_count += 1
                # Print every 50th delete to keep stdout clean
                if deleted_count % 50 == 0:
                    print(f"   Deleted {deleted_count} processed PDFs...")
            except Exception as e:
                print(f"⚠️ Error deleting {pdf_path.name}: {e}")
        else:
            skipped_count += 1
            
    space_saved_mb = total_space_saved / (1024 * 1024)
    print("\n================ CLEANUP SUMMARY ================")
    print(f"✅ Deleted PDF Files:  {deleted_count}")
    print(f"⏭️  Skipped PDF Files:  {skipped_count} (not processed or missing text)")
    print(f"💾 Disk Space Saved:   {space_saved_mb:.2f} MB")
    print("=================================================\n")

if __name__ == "__main__":
    cleanup()
