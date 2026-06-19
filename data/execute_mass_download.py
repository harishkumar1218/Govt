import json
import os
import requests
import urllib3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote

urllib3.disable_warnings()

def download_file(item):
    base_dir = Path("/Users/harish/Public/Govt/data/UPSC_Resources")
    target_dir = base_dir / item["exam_folder"] / item["category"]
    
    # Clean title for filename, but if it's too long or weird, fallback to original URL filename
    url = item["pdf_url"]
    original_filename = url.split('/')[-1]
    original_filename = unquote(original_filename)
    
    # Try to extract a clean filename from title, else use original URL name
    clean_title = "".join(c for c in item["title"] if c.isalnum() or c in " -_")[:50]
    filename = f"{clean_title}.pdf" if clean_title and clean_title != "PDF" else original_filename
    if not filename.endswith('.pdf'):
        filename += '.pdf'
        
    filepath = target_dir / filename
    
    if filepath.exists():
        return f"Skipped (Exists): {filename}"
        
    try:
        # Create dir safely inside threads
        target_dir.mkdir(parents=True, exist_ok=True)
        
        r = requests.get(url, verify=False, stream=True, timeout=15)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            return f"Downloaded: {filename} -> {item['exam_folder']}/{item['category']}"
        else:
            return f"Failed HTTP {r.status_code}: {url}"
    except Exception as e:
        return f"Error: {e} -> {url}"

def run_mass_download():
    map_file = '/Users/harish/Public/Govt/data/dry_run_map.json'
    if not os.path.exists(map_file):
        print("Error: dry_run_map.json not found!")
        return
        
    with open(map_file, 'r', encoding='utf-8') as f:
        all_pdfs = json.load(f)
        
    # Filter for NDA / NA only
    target_pdfs = [item for item in all_pdfs if item['exam_folder'] == '02_NDA_NA']
        
    total_files = len(target_pdfs)
    print(f"Starting mass download of {total_files} NDA/NA PDFs...")
    
    completed = 0
    success = 0
    
    # 20 concurrent connections to speed up downloading
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(download_file, item): item for item in target_pdfs}
        
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            
            if "Downloaded:" in result or "Skipped" in result:
                success += 1
                
            if completed % 100 == 0:
                print(f"[{completed}/{total_files}] Success: {success} | Latest: {result[:80]}")

    print(f"\nMass download complete! Successfully handled {success} out of {total_files} files.")

if __name__ == "__main__":
    run_mass_download()
