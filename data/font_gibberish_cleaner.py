import os
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from spellchecker import SpellChecker

spell = SpellChecker()

# Precompile regexes
word_re = re.compile(r'\b[a-zA-Z]+\b')
stand_caps_re = re.compile(r'\b[B-HJ-Z]\b') # Exclude A and I which are common standalone letters
artifact_words = ['frafead', 'wftnfea', 'uitede', 'frafra', 'arfeu', 'ofeafaa', 'fifee', 'aife']

def get_gibberish_score(line):
    score = 0
    line_clean = line.strip()
    if not line_clean: 
        return 0
        
    # Ignore purely structural lines
    if line_clean.startswith('--- Page'):
        return 0
        
    # 1. Artifact punctuation
    if '|' in line_clean: score += 2
    if '@' in line_clean: score += 1
    
    # 2. Known artifact words
    l_lower = line_clean.lower()
    for bad in artifact_words:
        if bad in l_lower: 
            score += 2
            
    words = word_re.findall(line_clean)
    if not words: 
        return score
        
    # 3. Average word length (gibberish is full of 1-3 letter artifacts)
    avg_len = sum(len(w) for w in words) / len(words)
    if avg_len < 3.8 and len(words) >= 4:
        score += 1
        
    # 4. Standalone capitals (often kruti dev mapping for half letters)
    stand_caps = stand_caps_re.findall(line_clean)
    if stand_caps:
        score += len(stand_caps)
        
    # 5. Mixed case words (e.g. Uitede, 1aMAA2)
    for w in words:
        if len(w) > 3 and not w.islower() and not w.isupper() and not w.istitle():
            score += 1
            
    # 6. Valid English word ratio
    long_words = [w.lower() for w in words if len(w) >= 3]
    if long_words:
        known = [w for w in long_words if w in spell]
        if len(known) / len(long_words) < 0.5:
            score += 2
            
    return score

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        cleaned_lines = []
        dropped_count = 0
        
        for line in lines:
            if get_gibberish_score(line) >= 2:
                dropped_count += 1
            else:
                cleaned_lines.append(line)
                
        if dropped_count > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
                
        return dropped_count
    except Exception as e:
        return f"Error on {filepath.name}: {e}"

def run_cleaner():
    base_dir = Path("/Users/harish/Public/Govt/procesed_docs")
    files = list(base_dir.rglob("*_text.txt"))
    
    total_files = len(files)
    print(f"Scanning {total_files} files for embedded font gibberish...")
    
    total_dropped = 0
    files_modified = 0
    
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(process_file, f): f for f in files}
        for future in as_completed(futures):
            res = future.result()
            if isinstance(res, int) and res > 0:
                total_dropped += res
                files_modified += 1
                
    print(f"Cleanup Complete! Removed {total_dropped} lines of font gibberish across {files_modified} files.")

if __name__ == "__main__":
    run_cleaner()
