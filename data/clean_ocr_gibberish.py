import os
import re
from pathlib import Path
from spellchecker import SpellChecker
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

spell = SpellChecker()

def is_gibberish(line):
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
    long_words = [w for w in words if len(w) >= 4]
    if long_words:
        known_long = [w for w in long_words if w in spell]
        if len(known_long) / len(long_words) < 0.5:
            return True
            
    return False

def clean_file(txt_path_str):
    txt_path = Path(txt_path_str)
    
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        cleaned_lines = []
        dropped_count = 0
        
        for line in lines:
            line_clean = line.strip()
            
            # Keep empty lines and page headers
            if not line_clean or line_clean.startswith('--- Page'):
                cleaned_lines.append(line)
                continue
                
            if is_gibberish(line_clean):
                dropped_count += 1
            else:
                cleaned_lines.append(line)
                
        # Only write if we actually dropped something
        if dropped_count > 0:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
                
        return f"Processed {txt_path.name} (Dropped {dropped_count} gibberish lines)"
        
    except Exception as e:
        return f"Error {txt_path.name}: {e}"

def run_cleanup(base_dir):
    base_path = Path(base_dir)
    print(f"Finding text files in {base_path}...")
    txt_files = list(base_path.rglob("*_text.txt"))
    total_files = len(txt_files)
    print(f"Found {total_files} text files. Starting cleanup...")

    completed = 0
    start_time = time.time()
    total_dropped = 0
    
    # Process files
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = {executor.submit(clean_file, str(p)): p for p in txt_files}
        
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            
            # Extract number of dropped lines if any
            match = re.search(r'Dropped (\d+)', result)
            if match:
                total_dropped += int(match.group(1))
            
            if completed % 100 == 0:
                print(f"[{completed}/{total_files}] Cleaned up {total_dropped} total gibberish lines so far...")

    total_time = time.time() - start_time
    print(f"\nCleanup complete! Dropped a total of {total_dropped} gibberish lines across {total_files} files in {total_time:.1f} seconds.")

if __name__ == "__main__":
    processed_dir = "/Users/harish/Public/Govt/procesed_docs"
    run_cleanup(processed_dir)
