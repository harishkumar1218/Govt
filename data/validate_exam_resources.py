#!/usr/bin/env python3
import os
import json
import re
from pathlib import Path

BASE_DIR = Path("/Users/harish/Public/Govt")
OUTPUT_DIR = BASE_DIR / "data/exam_resources"

TRACKS = ["upsc-civil-services", "ssc", "nda", "cds", "ese"]

def validate_syllabus_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        required = ["exam_slug", "exam_name", "stages"]
        for req in required:
            if req not in data:
                return False, f"Missing required field '{req}' in pattern JSON"
        return True, "Valid"
    except Exception as e:
        return False, f"Invalid JSON format: {e}"

def validate_answer_key_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return False, "Answer key must be a JSON object mapping keys to answers"
        for quiz_id, keys in data.items():
            if not isinstance(keys, dict):
                return False, f"Answer mapping for {quiz_id} must be a dictionary object"
            for q_num, ans in keys.items():
                if str(ans).upper() not in ["A", "B", "C", "D", "E"]:
                    return False, f"Invalid answer '{ans}' for question {q_num} under {quiz_id}"
        return True, "Valid"
    except Exception as e:
        return False, f"Invalid JSON format: {e}"

def validate_cutoff_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            return False, "Cutoffs must be a JSON list of objects"
        required = ["exam", "year", "stage", "category", "cutoff_marks"]
        for idx, item in enumerate(data):
            for req in required:
                if req not in item:
                    return False, f"Missing required field '{req}' in cutoff item at index {idx}"
        return True, "Valid"
    except Exception as e:
        return False, f"Invalid JSON format: {e}"

def check_question_sequence(text_content):
    # Find all "Question \d+:" patterns
    q_nums = [int(x) for x in re.findall(r'Question\s+(\d+)\s*:', text_content, re.IGNORECASE)]
    if not q_nums:
        # Fallback to general "\b\d+\." sequence check
        q_nums = [int(x) for x in re.findall(r'\b(\d+)\.\s+[A-Z]', text_content)]
        
    if not q_nums:
        return True, "No numbered questions found to sequence-check (Descriptive paper or syllabus)"
        
    # Check if they are sequential (e.g. 1, 2, 3...)
    # Allow some missing numbers due to OCR drops, but check for logical monotonicity
    out_of_order = 0
    for i in range(1, len(q_nums)):
        if q_nums[i] < q_nums[i - 1]:
            out_of_order += 1
            
    if out_of_order > len(q_nums) * 0.15: # Allow 15% tolerance
        return False, f"Highly non-sequential question numbering found: {q_nums[:10]}..."
    return True, "Questions are sequential"

def main():
    print("🚀 Starting resource validation audit...")
    
    validation_passed = True
    report = []
    
    checksums = {}
    duplicates = []
    
    total_files_audited = 0
    passed_count = 0
    failed_count = 0
    
    global_inventory_file = OUTPUT_DIR / "global_document_inventory.json"
    if not global_inventory_file.exists():
        print("❌ Global inventory JSON not found. Please run build_exam_metadata.py first.")
        return
        
    with open(global_inventory_file, 'r', encoding='utf-8') as f:
        inventory = json.load(f)
        
    print(f"📋 Loaded {len(inventory)} document metadata descriptors for validation.")
    
    for meta in inventory:
        total_files_audited += 1
        file_path = BASE_DIR / meta["file_path"]
        text_path = BASE_DIR / meta["text_path"] if meta["text_path"] else None
        
        file_ok = True
        reasons = []
        
        # 1. Check file exists and is not empty
        if not file_path.exists():
            file_ok = False
            reasons.append("File does not exist")
        elif file_path.stat().st_size == 0:
            file_ok = False
            reasons.append("File is empty (0 bytes)")
            
        # 2. Check metadata consistency
        # Ensure file matches track directory
        parent_slug = Path(meta["file_path"]).parts[2] # data/exam_resources/<track-slug>/...
        if parent_slug != meta["exam_slug"]:
            file_ok = False
            reasons.append(f"Cross-exam mixing! Found in directory '{parent_slug}' but metadata says exam_slug is '{meta['exam_slug']}'")
            
        # Check source URL exists
        if not meta["source_url"] or not meta["source_domain"]:
            file_ok = False
            reasons.append("Missing source URL or source domain metadata")
            
        # 3. Duplicate detection
        checksum = meta["checksum"]
        if checksum:
            if checksum in checksums:
                duplicates.append((str(file_path), checksums[checksum]))
            else:
                checksums[checksum] = str(file_path)
                
        # 4. Check validation by file type
        doc_type = meta["document_type"]
        if file_ok:
            if doc_type == "paper_pattern" and file_path.suffix.lower() == ".json":
                ok, err = validate_syllabus_json(file_path)
                if not ok:
                    file_ok = False
                    reasons.append(err)
            elif doc_type == "answer_key" and file_path.suffix.lower() == ".json":
                ok, err = validate_answer_key_json(file_path)
                if not ok:
                    file_ok = False
                    reasons.append(err)
            elif doc_type == "cutoff" and file_path.suffix.lower() == ".json":
                ok, err = validate_cutoff_json(file_path)
                if not ok:
                    file_ok = False
                    reasons.append(err)
                    
            # 5. Check PDF text sequence checks
            if meta.get("extraction_status") == "success" and "text_path" in meta:
                text_abs_path = BASE_DIR / meta["text_path"]
                if not text_abs_path.exists():
                    file_ok = False
                    reasons.append("Clean text file missing")
                elif text_abs_path.stat().st_size == 0:
                    file_ok = False
                    reasons.append("Clean text output is empty")
                else:
                    with open(text_abs_path, 'r', encoding='utf-8') as tf:
                        text_content = tf.read()
                    seq_ok, seq_msg = check_question_sequence(text_content)
                    if not seq_ok:
                        # Non-critical warning, log it but don't fail validation
                        reasons.append(f"Warning: {seq_msg}")
                        
        if file_ok:
            passed_count += 1
        else:
            failed_count += 1
            validation_passed = False
            report.append({
                "file": meta["file_path"],
                "reasons": reasons
            })
            
    print("\n📊 Validation Audit Summary:")
    print(f"   Audited   : {total_files_audited} files")
    print(f"   Passed    : {passed_count} files")
    print(f"   Failed    : {failed_count} files")
    print(f"   Duplicates: {len(duplicates)} files detected")
    
    if duplicates:
        print("\n👯 Duplicate files list:")
        for dup, orig in duplicates[:10]:
            print(f"   - Duplicate: {os.path.basename(dup)}")
            print(f"     Original : {os.path.basename(orig)}")
            
    if report:
        print("\n❌ Failed Validation Details:")
        for item in report[:15]:
            print(f"   - File: {item['file']}")
            for r in item['reasons']:
                print(f"     Reason: {r}")
        if len(report) > 15:
            print(f"   ... and {len(report) - 15} more failures.")
            
    if validation_passed:
        print("\n🎉 SUCCESS: All documents passed validation checks!")
    else:
        print("\n⚠️  WARNING: Some validation checks failed. Please check the logs.")

if __name__ == "__main__":
    main()
