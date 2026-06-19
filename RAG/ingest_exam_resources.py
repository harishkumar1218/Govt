#!/usr/bin/env python3
import os
import glob
import pickle
import json
import numpy as np
import torch
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from turbovec import IdMapIndex

BASE_DIR = Path("/Users/harish/Public/Govt")
OUTPUT_DIR = BASE_DIR / "data/exam_resources"
DB_DIR = BASE_DIR / "RAG/turbovec_index"

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

def load_all_metadata():
    print("🔍 Loading all metadata JSON files...")
    metadata_files = list(OUTPUT_DIR.rglob("metadata/*.json"))
    metadata_list = []
    for f in metadata_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                meta = json.load(file)
                metadata_list.append(meta)
        except Exception as e:
            print(f"Error reading metadata {f.name}: {e}")
    print(f"   Loaded {len(metadata_list)} metadata records.")
    return metadata_list

def select_core_documents(metadata_list):
    """Filter documents to build a high-quality, lightweight RAG index."""
    core_docs = []
    
    # Core subjects we definitely want to index
    core_subjects = [
        "general studies", "mathematics", "english", "general knowledge", 
        "quantitative aptitude", "essay", "csat", "reasoning", "general awareness"
    ]
    
    for meta in metadata_list:
        # Check if text is successfully extracted
        if not meta.get("text_path") or meta.get("extraction_status") != "success":
            continue
            
        doc_type = meta.get("document_type")
        subject = meta.get("subject", "").lower()
        year = meta.get("year", 2026)
        
        # Always include syllabus, cutoffs, notifications, and patterns
        if doc_type in ["syllabus", "cutoff", "notification", "paper_pattern", "essay"]:
            core_docs.append(meta)
        # For PYQs, only include the latest years (>= 2024) to keep the index extremely fast and lightweight
        elif doc_type == "previous_year_question":
            if year >= 2024:
                if any(cs in subject for cs in core_subjects) or meta.get("exam_slug") == "ssc":
                    core_docs.append(meta)
                
    print(f"🎯 Selected {len(core_docs)} core documents for RAG indexing (out of {len(metadata_list)}).")
    return core_docs

def main():
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Initializing SentenceTransformer with device: {device}...")
    model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    
    metadata_list = load_all_metadata()
    core_docs = select_core_documents(metadata_list)
    
    all_chunks_info = []
    
    for meta in tqdm(core_docs, desc="Reading files and chunking"):
        text_abs_path = BASE_DIR / meta["text_path"]
        try:
            with open(text_abs_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            if len(content.strip()) < 50:
                continue
                
            chunks = chunk_text(content)
            for i, chunk in enumerate(chunks):
                # Copy all metadata and attach chunk text
                chunk_info = meta.copy()
                chunk_info["text"] = chunk
                chunk_info["chunk_index"] = i
                all_chunks_info.append(chunk_info)
        except Exception as e:
            print(f"Error processing {text_abs_path.name}: {e}")
            
    num_chunks = len(all_chunks_info)
    if num_chunks == 0:
        print("No documents were processed. Turbovec index not created.")
        return
        
    print(f"Extracted {num_chunks} chunks. Computing embeddings in batch...")
    chunk_texts = [info["text"] for info in all_chunks_info]
    
    # Run batch encoding
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
    os.makedirs(DB_DIR, exist_ok=True)
    index_path = os.path.join(DB_DIR, "index.tvim")
    docs_path = os.path.join(DB_DIR, "docs.pkl")
    
    print(f"Saving Turbovec index to {index_path}...")
    index.write(index_path)
    
    print(f"Saving documents metadata to {docs_path}...")
    with open(docs_path, "wb") as f:
        pickle.dump(docs_dict, f)
        
    print(f"🎉 Ingestion complete! Saved {num_chunks} chunks in Turbovec RAG.")

if __name__ == "__main__":
    main()
