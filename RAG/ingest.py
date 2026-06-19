import os
import glob
import pickle
from pathlib import Path
from tqdm import tqdm
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from turbovec import IdMapIndex

def chunk_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= text_len:
            break
        start += (chunk_size - overlap)
    return chunks

def ingest_docs(data_dir, persist_directory):
    # Determine device
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Initializing SentenceTransformer with device: {device}...")
    model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    
    txt_files = glob.glob(os.path.join(data_dir, "**", "*_text.txt"), recursive=True)
    print(f"Found {len(txt_files)} text files.")
    
    all_chunks_info = []
    
    for file_path in tqdm(txt_files, desc="Reading files and chunking"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            if len(content.strip()) < 50:
                continue
                
            chunks = chunk_text(content)
            for i, chunk in enumerate(chunks):
                all_chunks_info.append({
                    "text": chunk,
                    "source": file_path,
                    "chunk_index": i
                })
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            
    num_chunks = len(all_chunks_info)
    if num_chunks == 0:
        print("No documents were processed. Turbovec index not created.")
        return
        
    print(f"Extracted {num_chunks} chunks. Computing embeddings in batch...")
    chunk_texts = [info["text"] for info in all_chunks_info]
    
    # Run batch encoding on MPS/CPU
    embeddings = model.encode(chunk_texts, batch_size=256, show_progress_bar=True)
    
    print(f"Building Turbovec index with {num_chunks} vectors...")
    index = IdMapIndex(dim=384, bit_width=4)
    
    docs_dict = {}
    ids_list = []
    for i, info in enumerate(all_chunks_info):
        docs_dict[i] = info
        ids_list.append(i)
        
    embeddings_arr = np.array(embeddings, dtype=np.float32)
    ids_arr = np.array(ids_list, dtype=np.uint64)
    index.add_with_ids(embeddings_arr, ids_arr)
    
    # Save index and docs mapping
    index_path = os.path.join(persist_directory, "index.tvim")
    docs_path = os.path.join(persist_directory, "docs.pkl")
    
    print(f"Saving Turbovec index to {index_path}...")
    index.write(index_path)
    
    print(f"Saving documents metadata to {docs_path}...")
    with open(docs_path, "wb") as f:
        pickle.dump(docs_dict, f)

if __name__ == "__main__":
    DATA_DIR = "/Users/harish/Public/Govt/procesed_docs"
    DB_DIR = "/Users/harish/Public/Govt/RAG/turbovec_index"
    
    os.makedirs(DB_DIR, exist_ok=True)
    ingest_docs(DATA_DIR, DB_DIR)
    print("Ingestion complete!")
