import json
import os
from pathlib import Path

BASE_DIR = Path("/Users/harish/Public/Govt")
metadata_files = list((BASE_DIR / "data/exam_resources").rglob("metadata/*.json"))

fixed_count = 0
for f in metadata_files:
    with open(f, 'r', encoding='utf-8') as file:
        meta = json.load(file)
        
    if "text_path" in meta:
        text_abs_path = BASE_DIR / meta["text_path"]
        if not text_abs_path.exists() or text_abs_path.stat().st_size == 0:
            if meta.get("extraction_status") == "success":
                meta["extraction_status"] = "failed"
                meta["notes"] = "Extraction failed: empty text file (likely image-only PDF)"
                with open(f, 'w', encoding='utf-8') as file:
                    json.dump(meta, file, indent=2)
                fixed_count += 1
                print(f"Marked {f.name} as failed.")

print(f"Fixed {fixed_count} metadata files.")
