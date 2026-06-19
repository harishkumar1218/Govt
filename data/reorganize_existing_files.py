#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
import urllib.parse

BASE_DIR = Path("UPSC_Resources/01_Civil_Services_IAS_IPS_IFS")

def reorganize():
    print("🧹 Correcting and starting reorganization of Civil Services files...")
    
    # Target folders
    prelims_gs1_dir = BASE_DIR / "03_Previous_Year_Papers/Prelims/GS_Paper_1"
    prelims_csat_dir = BASE_DIR / "03_Previous_Year_Papers/Prelims/CSAT_Paper_2"
    prelims_csat_dir.mkdir(parents=True, exist_ok=True)
    
    mains_optional_dir = BASE_DIR / "03_Previous_Year_Papers/Mains/Optional_Papers"
    mains_gs1_dir = BASE_DIR / "03_Previous_Year_Papers/Mains/GS_Paper_1"
    
    mains_gs_folders = {
        1: mains_gs1_dir,
        2: BASE_DIR / "03_Previous_Year_Papers/Mains/GS_Paper_2",
        3: BASE_DIR / "03_Previous_Year_Papers/Mains/GS_Paper_3",
        4: BASE_DIR / "03_Previous_Year_Papers/Mains/GS_Paper_4_Ethics"
    }
    
    for folder in mains_gs_folders.values():
        folder.mkdir(parents=True, exist_ok=True)
        
    # 1. Reorganize Prelims CSAT (Paper II) files from GS_Paper_1
    if prelims_gs1_dir.exists():
        for file in prelims_gs1_dir.iterdir():
            if file.is_file() and file.name.endswith(".pdf"):
                name_upper = file.name.upper()
                if any(x in name_upper for x in ["CSAT", "GS-II", "GS_II", "PAPER-II", "PAPER_II"]):
                    dest = prelims_csat_dir / file.name
                    print(f"  Moving Prelims CSAT: {file.name} -> {dest.relative_to(BASE_DIR)}")
                    shutil.move(str(file), str(dest))
                    
    # Helper to check a file and move to correct Mains GS folder
    def process_mains_file(file_path):
        name_upper = urllib.parse.unquote(file_path.name).upper()
        
        # Check in reverse order (IV, III, II, I) to avoid substring matching bugs
        gs_num = None
        if "GENERAL-STUDIES-PAPER-IV" in name_upper or "GENERAL_STUDIES_PAPER_IV" in name_upper or "GENERAL-STUDIES-PAPER-IV" in name_upper or "GENERAL-STUDIES-PAPER IV" in name_upper:
            gs_num = 4
        elif "GENERAL-STUDIES-PAPER-III" in name_upper or "GENERAL_STUDIES_PAPER_III" in name_upper or "GENERAL-STUDIES-PAPER-III" in name_upper or "GENERAL-STUDIES-PAPER III" in name_upper:
            gs_num = 3
        elif "GENERAL-STUDIES-PAPER-II" in name_upper or "GENERAL_STUDIES_PAPER_II" in name_upper or "GENERAL-STUDIES-PAPER-II" in name_upper or "GENERAL-STUDIES-PAPER II" in name_upper:
            gs_num = 2
        elif "GENERAL-STUDIES-PAPER-I" in name_upper or "GENERAL_STUDIES_PAPER_I" in name_upper or "GENERAL-STUDIES-PAPER-I" in name_upper or "GENERAL-STUDIES-PAPER I" in name_upper or "GENERAL-STUDIES-PAPER%20I" in name_upper:
            gs_num = 1
            
        if gs_num and gs_num in mains_gs_folders:
            dest = mains_gs_folders[gs_num] / file_path.name
            # Avoid self-moves
            if file_path.resolve() != dest.resolve():
                print(f"  Moving Mains GS: {file_path.name} -> {dest.relative_to(BASE_DIR)}")
                shutil.move(str(file_path), str(dest))

    # Scan Optional_Papers
    if mains_optional_dir.exists():
        for file in list(mains_optional_dir.iterdir()):
            if file.is_file() and file.name.endswith(".pdf"):
                process_mains_file(file)
                
    # Scan GS_Paper_1 (to correct any misclassified papers from previous run)
    if mains_gs1_dir.exists():
        for file in list(mains_gs1_dir.iterdir()):
            if file.is_file() and file.name.endswith(".pdf"):
                process_mains_file(file)
                
    print("✅ Reorganization complete!\n")

if __name__ == "__main__":
    reorganize()
