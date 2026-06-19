#!/usr/bin/env python3
import os
import hashlib
import json
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/harish/Public/Govt")
OUTPUT_DIR = BASE_DIR / "data/exam_resources"

TRACKS = {
    "upsc-civil-services": "UPSC Civil Services",
    "ssc": "Staff Selection Commission (SSC)",
    "nda": "National Defence Academy (NDA)",
    "cds": "Combined Defence Services (CDS)",
    "ese": "Engineering Services Examination (ESE)"
}

DOCUMENT_TYPE_MAP = {
    "syllabus": "syllabus",
    "previous_year_papers": "previous_year_question",
    "answer_keys": "answer_key",
    "cutoffs": "cutoff",
    "notifications": "notification",
    "essays": "essay",
    "pattern": "paper_pattern"
}

def md5_checksum(file_path):
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""

def parse_year(filename):
    # Find years in filename (e.g., 2011 to 2026)
    match = re.search(r'\b(20\d{2})\b', filename)
    if match:
        year = int(match.group(1))
        if 2010 <= year <= 2027:
            return year
    # Check for two digit years like "CSP-17" or "CSP17"
    match_2d = re.search(r'(?:CSP|CSM|NDA|CDS|ESE|CGL)[-_]?(\d{2})\b', filename, re.IGNORECASE)
    if match_2d:
        year = 2000 + int(match_2d.group(1))
        return year
    return None

def parse_stage(filename, path_str):
    combined = (filename + " " + path_str).lower()
    if "prelim" in combined or "csp" in combined or "stage 1" in combined or "tier 1" in combined or "tier-1" in combined:
        return "Prelims"
    elif "main" in combined or "csm" in combined or "stage 2" in combined or "tier 2" in combined or "tier-2" in combined:
        return "Mains"
    elif "interview" in combined or "personality" in combined or "ssb" in combined:
        return "Interview"
    return "Written"

def parse_subject_and_paper(filename, path_str, doc_type, track_slug):
    combined = (filename + " " + path_str).lower()
    
    paper = "Paper I"
    subject = "General Studies"
    
    # 1. UPSC Civil Services
    if track_slug == "upsc-civil-services":
        if "csat" in combined or "paper-ii" in combined or "paper_ii" in combined or "gs-ii" in combined:
            paper = "CSAT Paper II"
            subject = "CSAT"
        elif "essay" in combined:
            paper = "Paper I - Essay"
            subject = "Essay"
        elif "gs-i" in combined or "gs_i" in combined or "general-studies-i" in combined or "paper-i" in combined:
            paper = "General Studies Paper I"
            subject = "General Studies"
        elif "gs-ii" in combined or "gs_ii" in combined or "general-studies-ii" in combined:
            paper = "General Studies Paper II"
            subject = "General Studies"
        elif "gs-iii" in combined or "gs_iii" in combined or "general-studies-iii" in combined:
            paper = "General Studies Paper III"
            subject = "General Studies"
        elif "gs-iv" in combined or "gs_iv" in combined or "general-studies-iv" in combined or "ethics" in combined:
            paper = "General Studies Paper IV"
            subject = "Ethics"
            
    # 2. NDA
    elif track_slug == "nda":
        if "math" in combined:
            paper = "Mathematics"
            subject = "Mathematics"
        elif "gat" in combined or "general ability" in combined:
            paper = "General Ability Test"
            subject = "General Ability"
            
    # 3. CDS
    elif track_slug == "cds":
        if "english" in combined:
            paper = "English"
            subject = "English"
        elif "math" in combined:
            paper = "Elementary Mathematics"
            subject = "Mathematics"
        elif "gk" in combined or "general knowledge" in combined:
            paper = "General Knowledge"
            subject = "General Knowledge"
            
    # 4. ESE
    elif track_slug == "ese":
        if "general studies" in combined or "gs" in combined:
            paper = "Paper I"
            subject = "General Studies & Engineering Aptitude"
        else:
            paper = "Paper II"
            subject = "Engineering Discipline"
            
    # 5. SSC
    elif track_slug == "ssc":
        if "quant" in combined:
            paper = "Quantitative Aptitude"
            subject = "Quantitative Aptitude"
        elif "english" in combined:
            paper = "English Comprehension"
            subject = "English Comprehension"
        elif "reasoning" in combined:
            paper = "General Intelligence & Reasoning"
            subject = "Reasoning"
        elif "awareness" in combined:
            paper = "General Awareness"
            subject = "General Awareness"
            
    return paper, subject

def generate_metadata_for_track(track_slug):
    track_dir = OUTPUT_DIR / track_slug
    metadata_dir = track_dir / "metadata"
    text_dir = track_dir / "extracted_text"
    
    inventory = []
    
    for root, dirs, files in os.walk(track_dir):
        # Skip metadata and extracted_text folders
        if "metadata" in root or "extracted_text" in root:
            continue
            
        for file in files:
            # Skip hidden files
            if file.startswith("."):
                continue
                
            file_path = Path(root) / file
            
            # Map subfolder name to document type
            parent_folder_name = file_path.parent.name
            doc_type = DOCUMENT_TYPE_MAP.get(parent_folder_name, "previous_year_question")
            
            year = parse_year(file)
            if not year:
                # Default fallback
                year = 2026
                
            stage = parse_stage(file, str(file_path))
            paper, subject = parse_subject_and_paper(file, str(file_path), doc_type, track_slug)
            
            checksum = md5_checksum(file_path)
            
            # Text path
            txt_clean_path = text_dir / f"{file_path.stem}_clean_text.txt"
            
            # Source Domain & URL
            domain = "ssc.gov.in" if track_slug == "ssc" else "upsc.gov.in"
            source_url = f"https://www.{domain}"
            
            extraction_status = "not_applicable"
            if file_path.suffix.lower() == ".pdf":
                if txt_clean_path.exists() and txt_clean_path.stat().st_size > 0:
                    extraction_status = "success"
                else:
                    extraction_status = "failed"
            
            meta = {
                "exam_slug": track_slug,
                "exam_name": TRACKS[track_slug],
                "stage": stage,
                "paper": paper,
                "subject": subject,
                "year": year,
                "document_type": doc_type,
                "source_url": source_url,
                "source_domain": domain,
                "downloaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_verified": "2026-06-18",
                "file_path": str(file_path.relative_to(BASE_DIR)),
                "text_path": str(txt_clean_path.relative_to(BASE_DIR)) if txt_clean_path.exists() else "",
                "checksum": checksum,
                "extraction_status": extraction_status,
                "confidence_score": 1.0 if extraction_status == "success" else 0.0,
                "notes": f"Structured metadata for {file_path.name}"
            }
            
            # Save individual JSON in metadata/
            meta_file = metadata_dir / f"{file_path.name}.json"
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
                
            inventory.append(meta)
            
    # Save a manifest summary for this track
    manifest_file = track_dir / f"{track_slug}_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2)
        
    print(f"   Track '{track_slug}': Generated {len(inventory)} metadata descriptors.")
    return inventory

def main():
    print("🚀 Starting metadata generation pipeline...")
    
    total_docs = 0
    full_inventory = []
    
    for track_slug in TRACKS:
        print(f"🗂️  Generating metadata for track '{track_slug}'...")
        inv = generate_metadata_for_track(track_slug)
        total_docs += len(inv)
        full_inventory.extend(inv)
        
    # Write global document inventory manifest in data/exam_resources/
    global_manifest = OUTPUT_DIR / "global_document_inventory.json"
    with open(global_manifest, "w", encoding="utf-8") as f:
        json.dump(full_inventory, f, indent=2)
        
    print(f"🎉 Pipeline complete. Generated {total_docs} metadata JSON files and global inventory.")

if __name__ == "__main__":
    main()
