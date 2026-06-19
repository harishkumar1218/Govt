import os
import time
import re
import fitz
import pytesseract
from PIL import Image
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from spellchecker import SpellChecker

# Initialize global resources
spell = SpellChecker()

class PDFProcessorHandler(FileSystemEventHandler):
    def __init__(self, watch_dir, output_dir):
        self.watch_dir = Path(watch_dir)
        self.output_dir = Path(output_dir)

    def process_file(self, file_path_str):
        file_path = Path(file_path_str)
        if file_path.suffix.lower() != '.pdf':
            return
            
        print(f"[{time.strftime('%H:%M:%S')}] Detected new PDF: {file_path.name}")
        
        # Wait slightly to ensure file has finished copying into the folder
        time.sleep(2)
        
        try:
            # 1. Setup paths
            try:
                rel_path = file_path.relative_to(self.watch_dir)
                rel_dir = rel_path.parent
            except ValueError:
                # If file is not strictly inside watch_dir for some reason, just put it in root
                rel_dir = Path("")
                
            base_name = file_path.stem
            doc_output_dir = self.output_dir / rel_dir / base_name
            doc_output_dir.mkdir(parents=True, exist_ok=True)
            
            images_dir = doc_output_dir / "images"
            images_dir.mkdir(exist_ok=True)
            txt_path = doc_output_dir / f"{base_name}_text.txt"
            
            print(f"  -> Extracting with PyMuPDF...")
            
            # 2. Extract Data
            doc = fitz.open(str(file_path))
            full_text = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                full_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
                
                # Extract images
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    image_name = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                    with open(images_dir / image_name, "wb") as f:
                        f.write(image_bytes)
                        
            doc.close()
            
            raw_content = "".join(full_text)
            
            # 3. Check if OCR is needed
            clean_content = re.sub(r'--- Page \d+ ---', '', raw_content).strip()
            if len(clean_content) < 50:
                print(f"  -> Scanned PDF detected. Running OCR...")
                ocr_text = []
                images = list(images_dir.glob("*.*"))
                
                # Sort images
                def sort_key(img_p):
                    match = re.search(r'page(\d+)_img(\d+)', img_p.name)
                    if match:
                        return (int(match.group(1)), int(match.group(2)))
                    return (999, 999)
                images.sort(key=sort_key)
                
                current_page = -1
                for img_path in images:
                    page_match = re.search(r'page(\d+)_img', img_path.name)
                    p_num = int(page_match.group(1)) if page_match else "Unknown"
                    if p_num != current_page:
                        ocr_text.append(f"--- Page {p_num} (OCR) ---\n")
                        current_page = p_num
                    
                    try:
                        img = Image.open(str(img_path))
                        ocr_text.append(pytesseract.image_to_string(img) + "\n")
                    except Exception as e:
                        print(f"  -> Error OCRing image {img_path.name}: {e}")
                        
                raw_content = "".join(ocr_text)
            
            # 4. Clean Gibberish (Hindi OCR artifacts)
            print(f"  -> Cleaning OCR artifacts...")
            lines = raw_content.splitlines(keepends=True)
            cleaned_lines = []
            
            for line in lines:
                l_clean = line.strip()
                if not l_clean or l_clean.startswith('--- Page'):
                    cleaned_lines.append(line)
                    continue
                    
                # Heuristic logic
                is_gibberish = False
                if '|' in l_clean:
                    is_gibberish = True
                else:
                    words = re.findall(r'\b[a-zA-Z]+\b', l_clean.lower())
                    if words:
                        avg_len = sum(len(w) for w in words) / len(words)
                        if avg_len < 3.5 and len(words) > 5:
                            is_gibberish = True
                        else:
                            long_words = [w for w in words if len(w) >= 4]
                            if long_words:
                                known = [w for w in long_words if w in spell]
                                if len(known) / len(long_words) < 0.5:
                                    is_gibberish = True
                                    
                if not is_gibberish:
                    cleaned_lines.append(line)
                    
            # 5. Save Final Result
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
                
            # Clean empty image dir
            if not os.listdir(images_dir):
                images_dir.rmdir()
                
            print(f"[{time.strftime('%H:%M:%S')}] \u2705 Successfully processed and saved to: {doc_output_dir}")

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] \u274c Error processing {file_path.name}: {e}")

    def on_created(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.process_file(event.dest_path)

def start_watcher(watch_dir, output_dir):
    print(f"Starting PDF Auto-Processor Watcher...")
    print(f"Monitoring Directory: {watch_dir}")
    print(f"Output Directory  : {output_dir}")
    print("Press Ctrl+C to stop.")
    
    event_handler = PDFProcessorHandler(watch_dir, output_dir)
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping watcher...")
    observer.join()

if __name__ == "__main__":
    DATA_DIR = "/Users/harish/Public/Govt/data"
    PROCESSED_DIR = "/Users/harish/Public/Govt/procesed_docs"
    start_watcher(DATA_DIR, PROCESSED_DIR)
