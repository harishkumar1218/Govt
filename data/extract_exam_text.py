#!/usr/bin/env python3
import os
import re
import shutil
from pathlib import Path

BASE_DIR = Path("/Users/harish/Public/Govt")
INPUT_PROCESSED = BASE_DIR / "procesed_docs"
OUTPUT_DIR = BASE_DIR / "data/exam_resources"

# Attempt to load spellchecker, fallback to basic heuristics if missing
try:
    from spellchecker import SpellChecker
    spell = SpellChecker()
except ImportError:
    spell = None

def is_text_gibberish(line):
    # Tesseract often translates Hindi Danda (।) to a pipe (|)
    if '|' in line:
        return True
        
    words = re.findall(r'\b[a-zA-Z]+\b', line.lower())
    if not words: 
        return False
    
    # Gibberish lines usually consist of many short fragmented words
    avg_len = sum(len(w) for w in words) / len(words)
    if avg_len < 3.5 and len(words) > 5:
        return True
        
    # Check if the longer words in the line are valid English words
    if spell:
        long_words = [w for w in words if len(w) >= 4]
        if long_words:
            known_long = [w for w in long_words if w in spell]
            if len(known_long) / len(long_words) < 0.5:
                return True
            
    return False

def clean_ocr_text(content):
    lines = content.split("\n")
    cleaned_lines = []
    
    for line in lines:
        line_clean = line.strip()
        
        # Keep empty lines and page headers
        if not line_clean or line_clean.startswith('--- Page'):
            cleaned_lines.append(line)
            continue
            
        if is_text_gibberish(line_clean):
            continue
        
        # Heuristics: fix broken question numbers
        # e.g., "Q .1" or "Q1 ." -> "Question 1:"
        line_clean = re.sub(r'^Q\s*[\.\-]?\s*(\d+)\s*[\.\-]?\s*', r'Question \1: ', line_clean, flags=re.IGNORECASE)
        
        # Fix merged options
        # e.g. "A) Option A B) Option B" -> separate lines
        line_clean = re.sub(r'\s+([B-D]\))', r'\n\1', line_clean)
        
        cleaned_lines.append(line_clean)
        
    return "\n".join(cleaned_lines)

def extract_pdf_to_text(pdf_path, txt_raw_path, txt_clean_path):
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        full_text = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            full_text.append(f"--- Page {page_num + 1} ---\n")
            
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if b["type"] == 0:
                    for line in b["lines"]:
                        for span in line["spans"]:
                            full_text.append(span["text"])
                        full_text.append("\n")
                        
        raw_content = "".join(full_text)
        
        # Save raw text
        with open(txt_raw_path, "w", encoding="utf-8") as f:
            f.write(raw_content)
            
        # Clean and save clean text
        cleaned_content = clean_ocr_text(raw_content)
        with open(txt_clean_path, "w", encoding="utf-8") as f:
            f.write(cleaned_content)
            
        return "SUCCESS"
    except Exception as e:
        return f"ERROR: {e}"

def build_processed_index():
    """Build a map of pdf_stem -> txt_file_path for O(1) lookup."""
    print("🔍 Pre-indexing existing processed text files...")
    txt_map = {}
    if not INPUT_PROCESSED.exists():
        return txt_map
        
    for root, dirs, files in os.walk(INPUT_PROCESSED):
        # The parent directory of the text file matches the pdf_stem
        parent_name = os.path.basename(root)
        for file in files:
            if file.lower().endswith(".txt"):
                txt_path = Path(root) / file
                # Save both by parent folder name (stem) and the filename stem
                txt_map[parent_name] = txt_path
                txt_map[txt_path.stem.replace("_text", "")] = txt_path
                
    print(f"   Indexed {len(txt_map)} processed text references.")
    return txt_map

def process_track(track_slug, processed_txt_map):
    track_dir = OUTPUT_DIR / track_slug
    pdf_count = 0
    extracted_count = 0
    skipped_count = 0
    
    for root, dirs, files in os.walk(track_dir):
        # Skip extracted_text and metadata
        if "extracted_text" in root or "metadata" in root:
            continue
            
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_path = Path(root) / file
                pdf_count += 1
                
                txt_dir = track_dir / "extracted_text"
                txt_raw = txt_dir / f"{pdf_path.stem}_raw_text.txt"
                txt_clean = txt_dir / f"{pdf_path.stem}_clean_text.txt"
                
                # Check if we already have it
                if txt_clean.exists() and txt_clean.stat().st_size > 0:
                    skipped_count += 1
                    continue
                
                # 1. Attempt to find existing text in pre-indexed processed map
                pdf_stem = pdf_path.stem
                txt_src = processed_txt_map.get(pdf_stem)
                if txt_src and txt_src.exists():
                    shutil.copy(txt_src, txt_clean)
                    if not txt_raw.exists():
                        shutil.copy(txt_src, txt_raw)
                    extracted_count += 1
                else:
                    # 2. Extract from PDF using pymupdf
                    res = extract_pdf_to_text(pdf_path, txt_raw, txt_clean)
                    if res == "SUCCESS":
                        extracted_count += 1
                    else:
                        print(f"  Failed to extract {pdf_path.name}: {res}")
                        
    return pdf_count, extracted_count, skipped_count

def main():
    print("🚀 Starting text extraction and cleanup pipeline...")
    processed_txt_map = build_processed_index()
    
    total_pdfs = 0
    total_extracted = 0
    total_skipped = 0
    
    for track_slug in TRACKS:
        print(f"📄 Processing track '{track_slug}'...")
        pdfs, extracted, skipped = process_track(track_slug, processed_txt_map)
        print(f"   Track '{track_slug}': {pdfs} PDFs, {extracted} newly extracted/copied, {skipped} skipped.")
        total_pdfs += pdfs
        total_extracted += extracted
        total_skipped += skipped
        
    print(f"🎉 Pipeline complete. Total PDFs: {total_pdfs}, Extracted/Copied: {total_extracted}, Skipped: {total_skipped}.")

TRACKS = ["upsc-civil-services", "ssc", "nda", "cds", "ese"]

if __name__ == "__main__":
    main()
