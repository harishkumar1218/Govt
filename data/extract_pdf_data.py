import os
import fitz  # PyMuPDF
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

def process_single_pdf(pdf_path_str, input_base_dir_str, output_base_dir_str):
    pdf_path = Path(pdf_path_str)
    input_base_dir = Path(input_base_dir_str)
    output_base_dir = Path(output_base_dir_str)
    
    # Calculate relative path
    rel_path = pdf_path.relative_to(input_base_dir)
    rel_dir = rel_path.parent
    base_name = pdf_path.stem
    
    # Create the structured output path
    # e.g. processed_docs / 03_Previous_Year_Papers / Prelims / GS_Paper_1 / CSP-17
    doc_output_dir = output_base_dir / rel_dir / base_name
    doc_output_dir.mkdir(parents=True, exist_ok=True)
    
    images_dir = doc_output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    txt_path = doc_output_dir / f"{base_name}_text.txt"
    
    # Skip if already fully processed (basic check)
    if txt_path.exists() and txt_path.stat().st_size > 0:
        return f"Skipped: {rel_path} (Already processed)"
        
    try:
        doc = fitz.open(str(pdf_path))
        full_text = []
        
        # Iterate through pages
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
                    image_path = images_dir / image_name
                    
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                        
                    full_text.append(f"\n[Image data with corresponding image name: {image_name}]\n")
                    img_index += 1
                    
        # Save full text
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("".join(full_text))
            
        # Clean up images dir if empty
        if not os.listdir(images_dir):
            images_dir.rmdir()
            
        return f"Success: {rel_path}"
        
    except Exception as e:
        return f"Error processing {rel_path}: {e}"

def process_pdfs_recursive(input_dir, output_dir):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    print(f"Finding PDF files in {input_path}...")
    pdf_files = list(input_path.rglob("*.pdf"))
    total_files = len(pdf_files)
    print(f"Found {total_files} PDF files. Starting extraction...")

    # Using multiprocessing for CPU-bound PDF extraction task
    completed = 0
    start_time = time.time()
    
    # Use ProcessPoolExecutor to max out CPU cores
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                process_single_pdf, 
                str(pdf), 
                str(input_path), 
                str(output_path)
            ): pdf for pdf in pdf_files
        }
        
        # Process results as they complete
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            
            # Print progress every 50 files or on errors to avoid console spam
            if completed % 50 == 0 or "Error" in result:
                elapsed = time.time() - start_time
                rate = completed / elapsed
                rem_files = total_files - completed
                est_rem_time = rem_files / rate if rate > 0 else 0
                print(f"[{completed}/{total_files}] {result} | Est. remaining: {est_rem_time:.0f}s")

    print(f"\nProcessing complete! {total_files} files processed in {time.time() - start_time:.1f} seconds.")

if __name__ == "__main__":
    input_directory = "/Users/harish/Public/Govt/data/UPSC_Resources/01_Civil_Services_IAS_IPS_IFS"
    output_directory = "/Users/harish/Public/Govt/procesed_docs"
    process_pdfs_recursive(input_directory, output_directory)
