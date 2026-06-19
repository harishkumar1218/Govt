import os
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import pytesseract
from PIL import Image

def process_single_ocr(txt_path_str):
    txt_path = Path(txt_path_str)
    
    # Check if file exists
    if not txt_path.exists():
        return f"File missing: {txt_path.name}"
        
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Clean content to check if it's actually empty
        clean_content = re.sub(r'--- Page \d+ ---', '', content)
        clean_content = re.sub(r'\[Image data with corresponding image name: [^\]]+\]', '', clean_content).strip()
        
        # If there's substantial text, skip OCR
        if len(clean_content) >= 50:
            return f"Skipped: {txt_path.name} (Has text)"
            
        # Needs OCR. Locate images dir.
        images_dir = txt_path.parent / "images"
        if not images_dir.exists() or not images_dir.is_dir():
            return f"Skipped: {txt_path.name} (No images dir)"
            
        images = list(images_dir.glob("*.*"))
        if not images:
            return f"Skipped: {txt_path.name} (Images dir empty)"
            
        # Sort images by page number, then image index
        # e.g., page1_img1.jpeg -> (1, 1)
        def sort_key(img_path):
            name = img_path.name
            match = re.search(r'page(\d+)_img(\d+)', name)
            if match:
                return (int(match.group(1)), int(match.group(2)))
            return (999, 999) # fallback
            
        images.sort(key=sort_key)
        
        new_content = content
        
        for img_path in images:
            img_name = img_path.name
            
            try:
                # Run Tesseract OCR
                img = Image.open(str(img_path))
                text = pytesseract.image_to_string(img)
                ocr_block = f"\n--- OCR Text ---\n{text}\n--- End OCR Text ---\n"
                
                placeholder = f"[Image data with corresponding image name: {img_name}]"
                if placeholder in new_content:
                    new_content = new_content.replace(placeholder, placeholder + ocr_block)
                else:
                    new_content += f"\n{placeholder}{ocr_block}"
            except Exception as img_e:
                error_msg = f"\n[Error reading image {img_name}: {img_e}]\n"
                placeholder = f"[Image data with corresponding image name: {img_name}]"
                if placeholder in new_content:
                    new_content = new_content.replace(placeholder, placeholder + error_msg)
                else:
                    new_content += f"\n{placeholder}{error_msg}"
                
        # Overwrite the text file with updated results
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return f"Success OCR: {txt_path.name}"
        
    except Exception as e:
        return f"Error {txt_path.name}: {e}"

def run_ocr_pipeline(base_dir):
    base_path = Path(base_dir)
    print(f"Finding text files in {base_path}...")
    txt_files = list(base_path.rglob("*_text.txt"))
    total_files = len(txt_files)
    print(f"Found {total_files} text files. Filtering and starting OCR pipeline...")

    # Count how many actually need OCR first for better progress tracking
    to_process = []
    for txt_path in txt_files:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        clean_content = re.sub(r'--- Page \d+ ---', '', content)
        clean_content = re.sub(r'\[Image data with corresponding image name: [^\]]+\]', '', clean_content).strip()
        if len(clean_content) < 50:
            to_process.append(str(txt_path))
            
    total_to_process = len(to_process)
    print(f"Total documents requiring OCR: {total_to_process}")
    
    if total_to_process == 0:
        print("Nothing to process.")
        return

    completed = 0
    start_time = time.time()
    
    # Leave 1 core free so the system remains responsive
    max_workers = max(1, os.cpu_count() - 1)
    print(f"Running on {max_workers} CPU cores...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_ocr, path_str): path_str 
            for path_str in to_process
        }
        
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            
            # Print every 10 items or on error
            if completed % 10 == 0 or "Error" in result:
                elapsed = time.time() - start_time
                rate = completed / elapsed
                rem_files = total_to_process - completed
                est_rem_time = rem_files / rate if rate > 0 else 0
                
                # Format time string nicely
                if est_rem_time > 3600:
                    time_str = f"{est_rem_time/3600:.1f} hours"
                elif est_rem_time > 60:
                    time_str = f"{est_rem_time/60:.1f} mins"
                else:
                    time_str = f"{est_rem_time:.0f} secs"
                    
                print(f"[{completed}/{total_to_process}] {result} | Est. remaining: {time_str}")

    total_time = time.time() - start_time
    print(f"\nOCR Pipeline complete! Processed {total_to_process} files in {total_time/60:.1f} minutes.")

if __name__ == "__main__":
    processed_dir = "/Users/harish/Public/Govt/procesed_docs"
    run_ocr_pipeline(processed_dir)
