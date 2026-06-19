import os
import json
import requests
import urllib3
import fitz
import pytesseract
from PIL import Image
import tempfile
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from urllib.parse import unquote
from spellchecker import SpellChecker

urllib3.disable_warnings()
spell = SpellChecker()

def is_gibberish(line):
    if '|' in line:
        return True
    words = re.findall(r'\b[a-zA-Z]+\b', line.lower())
    if not words: 
        return False
    avg_len = sum(len(w) for w in words) / len(words)
    if avg_len < 3.5 and len(words) > 5:
        return True
    long_words = [w for w in words if len(w) >= 4]
    if long_words:
        known_long = [w for w in long_words if w in spell]
        if len(known_long) / len(long_words) < 0.5:
            return True
    return False

def process_single_file(item):
    base_out_dir = Path("/Users/harish/Public/Govt/procesed_docs")
    target_dir = base_out_dir / item["exam_folder"] / item["category"]
    
    url = item["pdf_url"]
    original_filename = unquote(url.split('/')[-1])
    clean_title = "".join(c for c in item["title"] if c.isalnum() or c in " -_")[:50]
    base_name = clean_title if clean_title and clean_title != "PDF" else original_filename.replace('.pdf', '')
    
    txt_filename = f"{base_name}_text.txt"
    txt_filepath = target_dir / txt_filename
    
    # Skip if we already processed it
    if txt_filepath.exists():
        return f"Skipped (Exists): {txt_filename}"
        
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Use a secure, auto-cleaning temporary directory
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmp_dir = Path(tmpdirname)
        pdf_path = tmp_dir / "temp.pdf"
        
        # 1. Download directly to temp folder
        try:
            r = requests.get(url, verify=False, stream=True, timeout=15)
            if r.status_code == 200:
                with open(pdf_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
            else:
                return f"Failed HTTP {r.status_code}: {url}"
        except Exception as e:
            return f"Download Error: {e} -> {url}"
            
        # 2. Extract with PyMuPDF
        try:
            doc = fitz.open(str(pdf_path))
            full_text = []
            images_dir = tmp_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            images_perm_dir = target_dir / f"{base_name}_images"
            images_perm_dir.mkdir(exist_ok=True)

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                full_text.append(f"--- Page {page_num + 1} ---\n")
                
                blocks = page.get_text("dict")["blocks"]
                img_index = 0
                for b in blocks:
                    if b["type"] == 0:
                        for line in b["lines"]:
                            for span in line["spans"]:
                                full_text.append(span["text"])
                            full_text.append("\n")
                    elif b["type"] == 1:
                        image_bytes = b["image"]
                        image_ext = b["ext"]
                        image_name = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                        
                        # Save temporarily for OCR and permanently for user
                        temp_path = images_dir / image_name
                        perm_path = images_perm_dir / image_name
                        
                        with open(temp_path, "wb") as f:
                            f.write(image_bytes)
                        with open(perm_path, "wb") as f:
                            f.write(image_bytes)
                            
                        full_text.append(f"\n[Image data with corresponding image name: {image_name}]\n")
                        img_index += 1
            doc.close()
            raw_content = "".join(full_text)
            
            # 3. Check for Scanned PDF & Run OCR on the fly
            clean_content = re.sub(r'--- Page \d+ ---', '', raw_content)
            clean_content = re.sub(r'\[Image data with corresponding image name: [^\]]+\]', '', clean_content).strip()
            if len(clean_content) < 50:
                images = list(images_dir.glob("*.*"))
                
                def sort_key(img_p):
                    match = re.search(r'page(\d+)_img(\d+)', img_p.name)
                    return (int(match.group(1)), int(match.group(2))) if match else (999, 999)
                images.sort(key=sort_key)
                
                for img_path in images:
                    img_name = img_path.name
                    try:
                        img = Image.open(str(img_path))
                        text = pytesseract.image_to_string(img)
                        ocr_block = f"\n--- OCR Text ---\n{text}\n--- End OCR Text ---\n"
                        placeholder = f"[Image data with corresponding image name: {img_name}]"
                        if placeholder in raw_content:
                            raw_content = raw_content.replace(placeholder, placeholder + ocr_block)
                        else:
                            raw_content += f"\n{placeholder}{ocr_block}"
                    except:
                        pass
                        
            # Clean up permanent images directory if empty
            if not os.listdir(images_perm_dir):
                images_perm_dir.rmdir()
                
            # 4. Clean Gibberish (Hindi OCR Artifacts)
            lines = raw_content.splitlines(keepends=True)
            cleaned_lines = []
            for line in lines:
                l_clean = line.strip()
                if not l_clean or l_clean.startswith('--- Page'):
                    cleaned_lines.append(line)
                    continue
                if not is_gibberish(l_clean):
                    cleaned_lines.append(line)
                    
            # 5. Save final pristine TXT file to permanent storage
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
                
            # Note: At the end of the `with tempfile.TemporaryDirectory():` block,
            # python automatically and permanently deletes `temp.pdf` and the `images/` directory.
                
            return f"Processed: {txt_filename} -> {item['exam_folder']}/{item['category']}"
            
        except Exception as e:
            return f"Processing Error: {e} -> {url}"

def run_stream_processor():
    map_file = '/Users/harish/Public/Govt/data/dry_run_map.json'
    if not os.path.exists(map_file):
        print("Error: dry_run_map.json not found!")
        return
        
    with open(map_file, 'r', encoding='utf-8') as f:
        all_pdfs = json.load(f)
        
    total_files = len(all_pdfs)
    print(f"Starting streaming processing of {total_files} PDFs...")
    print("Files will be downloaded to /tmp, OCR'd in memory, saved to procesed_docs as .txt, and original PDFs instantly deleted.")
    
    completed = 0
    success = 0
    
    # Use ProcessPoolExecutor because OCR is CPU-heavy.
    # Leave 2 cores free so the Mac doesn't completely freeze for days.
    max_w = max(1, os.cpu_count() - 2)
    with ProcessPoolExecutor(max_workers=max_w) as executor:
        futures = {executor.submit(process_single_file, item): item for item in all_pdfs}
        
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            
            if "Processed:" in result or "Skipped" in result:
                success += 1
                
            if completed % 10 == 0:
                print(f"[{completed}/{total_files}] Success: {success} | Latest: {result[:80]}")

if __name__ == "__main__":
    run_stream_processor()
