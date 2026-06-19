#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        UPSC CIVIL SERVICES RESOURCE SYNC & DOWNLOADER            ║
║       Downloads all missing CSE resources (2012 - 2026)          ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import re
import time
import shutil
import logging
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────────────────────────────
# Configuration & Paths
# ─────────────────────────────────────────────────────────────────

BASE_DIR = Path("UPSC_Resources/01_Civil_Services_IAS_IPS_IFS")
LOG_FILE = Path("UPSC_Resources/download_log.txt")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ─────────────────────────────────────────────────────────────────
# Direct Verified Resource Listings
# ─────────────────────────────────────────────────────────────────

NOTIFICATIONS = {
    2026: "https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2026-Engl-040226.pdf",
    2025: "https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2025-Engl-220125.pdf",
    2024: "https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2024_Engl_140224.pdf",
    2023: "https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2023_Engl_010223.pdf",
    2022: "https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2022_Engl_020222.pdf",
    2021: "https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2021_Engl_040321.pdf",
    2020: "https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2020_Engl_120220.pdf"
}

ANSWER_KEYS = {
    2025: [
        "https://www.upsc.gov.in/sites/default/files/AnsKeyCivilServicesP-Exam-2025-GeneralStudies-I-130526.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKeyCivilServicesP-Exam-2025-GeneralStudies-II-130526.pdf"
    ],
    2024: [
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2024-GeneralStudies-I-210525.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2024-GeneralStudies-II-210525.pdf"
    ],
    2023: [
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2023-GeneralStudies-I-180424.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2023-GeneralStudies-II-180424.pdf"
    ],
    2022: [
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2022-GeneralStudies-I-240523.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2022-GeneralStudies-II-240523.pdf"
    ],
    2021: [
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2021-GeneralStudies-I-300522.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2021-GeneralStudies-II-300522.pdf"
    ],
    2020: [
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2020-GeneralStudies-I-270921.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2020-GeneralStudies-II-270921.pdf"
    ]
}

CUTOFFS = {
    2025: "https://www.upsc.gov.in/sites/default/files/CSE_2025_Cut-OffMks_Eng_09032026.pdf",
    2024: "https://www.upsc.gov.in/sites/default/files/CutOff-CSE-2024-Engl-220425.pdf",
    2023: "https://www.upsc.gov.in/sites/default/files/CutOff-CSE-23-engl-180424.pdf",
    2022: "https://www.upsc.gov.in/sites/default/files/CutOff-CSE-22-Engl-230523.pdf",
    2021: "https://www.upsc.gov.in/sites/default/files/CutOff-CSE-21-engl-300522.pdf",
    2020: "https://www.upsc.gov.in/sites/default/files/CutOff-CSE-20-engl-270921.pdf",
    2019: "https://www.upsc.gov.in/sites/default/files/Cut_Off_Marks_CS2019_Eng.pdf",
    2018: "https://www.upsc.gov.in/sites/default/files/CutOff-CSE-2018-Engl-R.pdf",
    2017: "https://www.upsc.gov.in/sites/default/files/Cutoff-CSE-2017-Engl.pdf",
    2016: "https://www.upsc.gov.in/sites/default/files/CutOff_CSE_2016_Engl_040717.pdf",
    2015: "https://www.upsc.gov.in/sites/default/files/Old-CutOff_CSM_2015_Engl_040717_2.pdf",
    2014: "https://www.upsc.gov.in/sites/default/files/Cutoff_CS_2014.pdf",
    2013: "https://www.upsc.gov.in/sites/default/files/Cut-off-cs-2013.pdf",
    2012: "https://www.upsc.gov.in/sites/default/files/cut-off%20marks%20cs2012.pdf"
}

# ─────────────────────────────────────────────────────────────────
# Refined Smart Categorization Rules for CSE
# ─────────────────────────────────────────────────────────────────

CATEGORY_RULES = [
    # Civil Services Prelims (CSAT must be checked before GS-I)
    (r"CSP.*CSAT|CSP.*GS.*II|CSP.*PAPER.II|QP.CSP.*CSAT",
     "03_Previous_Year_Papers/Prelims/CSAT_Paper_2"),
    (r"CSP.*GS.*I(?!I|V)|CSP.*GENERAL.STUDIES.*PAPER.I(?!I|V)|QP.CSP.*GS-I(?!I|V)",
     "03_Previous_Year_Papers/Prelims/GS_Paper_1"),

    # Civil Services Mains
    (r"CSM.*ESSAY|IFSM.*ESSAY",
     "03_Previous_Year_Papers/Mains/Essay_Paper"),
    (r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUDIES).I(?!I|V)|(?:GS|GENERAL.STUDIES).I(?!I|V).*(?:CSM|QP.*CSM)",
     "03_Previous_Year_Papers/Mains/GS_Paper_1"),
    (r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUDIES).II(?!I)|(?:GS|GENERAL.STUDIES).II(?!I).*(?:CSM|QP.*CSM)",
     "03_Previous_Year_Papers/Mains/GS_Paper_2"),
    (r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUDIES).III|(?:GS|GENERAL.STUDIES).III.*(?:CSM|QP.*CSM)",
     "03_Previous_Year_Papers/Mains/GS_Paper_3"),
    (r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUDIES).IV|ETHICS.*(?:CSM|QP.*CSM)|(?:CSM|QP.*CSM).*ETHICS",
     "03_Previous_Year_Papers/Mains/GS_Paper_4_Ethics"),
     
    # Indian Forest Service Mains
    (r"IFoS|IFSM|FOREST.SERVICE",
     "03_Previous_Year_Papers/Mains/IFS_Forest_Service"),
]

DEFAULT_CATEGORY = "03_Previous_Year_Papers/Mains/Optional_Papers"

def setup_logging():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

def get_subfolder_for_pyq(filename: str) -> str:
    name_upper = filename.upper()
    for pattern, subfolder in CATEGORY_RULES:
        if re.search(pattern, name_upper, re.IGNORECASE):
            return subfolder
    return DEFAULT_CATEGORY

# ─────────────────────────────────────────────────────────────────
# Downloader Core
# ─────────────────────────────────────────────────────────────────

def download_file(url: str, dest_subfolder: str, custom_filename: str = None, retries: int = 3) -> dict:
    filename = custom_filename if custom_filename else url.split("/")[-1]
    filename = urllib_unquote(filename)
    dest_dir = BASE_DIR / dest_subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename

    if dest_path.exists() and dest_path.stat().st_size > 1024:
        return {"file": filename, "status": "SKIPPED", "path": str(dest_path)}

    for attempt in range(1, retries + 1):
        try:
            resp = SESSION.get(url, timeout=30, stream=True)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "")
                if "html" in content_type and "pdf" not in content_type:
                    return {"file": filename, "status": "FAILED", "reason": "HTML instead of PDF", "url": url}

                downloaded = 0
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=16384):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                return {
                    "file": filename,
                    "status": "SUCCESS",
                    "size_kb": round(downloaded / 1024, 1),
                    "path": str(dest_path),
                }
            elif resp.status_code == 404:
                return {"file": filename, "status": "NOT_FOUND", "url": url}
            else:
                if attempt < retries:
                    time.sleep(2 * attempt)
                else:
                    return {"file": filename, "status": "FAILED", "reason": f"HTTP {resp.status_code}", "url": url}
        except Exception as e:
            if attempt < retries:
                time.sleep(2 * attempt)
            else:
                return {"file": filename, "status": "FAILED", "reason": str(e), "url": url}

    return {"file": filename, "status": "FAILED", "reason": "Max retries reached", "url": url}

def urllib_unquote(s):
    import urllib.parse
    return urllib.parse.unquote(s)

# ─────────────────────────────────────────────────────────────────
# PYQ Web Scraper (Crawling Live Pages & Archives)
# ─────────────────────────────────────────────────────────────────

def scrape_pyq_page(url: str, page_num: int) -> list[tuple[str, str]]:
    """Fetch all PDF links for Civil Services / Forest Service exams on a page."""
    logging.info(f"🔍 Scraping PYQ page {page_num}: {url}")
    results = []
    try:
        resp = SESSION.get(url, timeout=20)
        if resp.status_code != 200:
            logging.warning(f"⚠️  Failed to fetch PYQ page {page_num}: {resp.status_code}")
            return []
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        tables = soup.find_all('table')
        
        for table in tables:
            caption = table.find('caption')
            caption_text = caption.get_text(strip=True).lower() if caption else ""
            
            # Filter specifically for Civil Services and Indian Forest Service
            if "civil services" in caption_text or "forest service" in caption_text:
                for li in table.find_all('li'):
                    a_links = li.find_all('a', href=re.compile(r'\.pdf$', re.I))
                    for a in a_links:
                        pdf_url = a.get('href')
                        if not pdf_url.startswith("http"):
                            pdf_url = "https://www.upsc.gov.in" + pdf_url if pdf_url.startswith("/") else f"https://www.upsc.gov.in/{pdf_url}"
                        results.append(pdf_url)
    except Exception as e:
        logging.error(f"❌ Error scraping page {page_num}: {e}")
    return list(set(results))

def collect_all_pyq_links() -> list[str]:
    logging.info("📚 Discovering question paper PDFs from live site and archives...")
    all_links = set()
    
    # Scrape first 5 pages of previous question papers (active/recent years)
    for p in range(5):
        url = "https://www.upsc.gov.in/examinations/previous-question-papers" if p == 0 else f"https://www.upsc.gov.in/examinations/previous-question-papers?page={p}"
        links = scrape_pyq_page(url, p)
        all_links.update(links)
        logging.info(f"   Found {len(links)} PDFs (Total unique: {len(all_links)})")
        time.sleep(0.3)
        
    # Scrape archives page
    archive_url = "https://www.upsc.gov.in/examinations/previous-question-papers/archives"
    archive_links = scrape_pyq_page(archive_url, "Archives")
    all_links.update(archive_links)
    logging.info(f"   Found {len(archive_links)} PDFs in Archives (Total unique: {len(all_links)})")
    
    return list(all_links)

# ─────────────────────────────────────────────────────────────────
# Batch Executer
# ─────────────────────────────────────────────────────────────────

def run_download_batch(downloads: list[tuple[str, str, str]], label: str, workers: int = 4):
    """Downloads a list of (url, dest_subfolder, custom_filename) in parallel."""
    total = len(downloads)
    logging.info(f"\n🚀 Starting batch: {label} ({total} files, {workers} workers)...")
    
    results = {"SUCCESS": 0, "SKIPPED": 0, "FAILED": 0, "NOT_FOUND": 0}
    completed = 0
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(download_file, url, subfolder, name): (url, name) for url, subfolder, name in downloads}
        for future in as_completed(futures):
            completed += 1
            res = future.result()
            status = res["status"]
            results[status] += 1
            
            icon = {"SUCCESS": "✅", "SKIPPED": "⏭️", "FAILED": "❌", "NOT_FOUND": "🔍"}.get(status, "?")
            msg = f"[{completed:>4}/{total}] {icon} {res['file']} -> {status}"
            if status == "FAILED":
                msg += f" (Reason: {res.get('reason','')})"
            elif status == "SUCCESS":
                msg += f" ({res.get('size_kb', 0)} KB)"
            logging.info(msg)
            
    logging.info(f"📊 Batch {label} summary: Success={results['SUCCESS']}, Skipped={results['SKIPPED']}, Failed={results['FAILED']}, Not Found={results['NOT_FOUND']}")
    return results

# ─────────────────────────────────────────────────────────────────
# Main Sync Flow
# ─────────────────────────────────────────────────────────────────

def main():
    setup_logging()
    logging.info("==================================================================")
    logging.info("        UPSC CIVIL SERVICES RESOURCE SYNC & DOWNLOADER            ")
    logging.info("==================================================================")
    
    # 1. Prepare Notifications batch
    notif_batch = []
    for year, url in NOTIFICATIONS.items():
        name = f"Notice-CSE-{year}.pdf"
        # We save it in Notifications & Schedule
        notif_batch.append((url, "02_Notifications_&_Schedule", name))
        
    # 2. Prepare Answer Keys batch
    ak_batch = []
    for year, urls in ANSWER_KEYS.items():
        for url in urls:
            ak_batch.append((url, "04_Answer_Keys", None))
            
    # 3. Prepare Cutoffs batch
    co_batch = []
    for year, url in CUTOFFS.items():
        name = f"Cutoff-CSE-{year}.pdf"
        co_batch.append((url, "05_Cut_Off_Marks", name))
        
    # 4. Prepare Question Papers batch by scraping
    pyq_urls = collect_all_pyq_links()
    pyq_batch = []
    for url in pyq_urls:
        filename = url.split("/")[-1]
        subfolder = get_subfolder_for_pyq(filename)
        pyq_batch.append((url, subfolder, None))
        
    # Run batches
    logging.info("\n--- STEP 1: DOWNLOADING NOTIFICATIONS ---")
    run_download_batch(notif_batch, "Notifications")
    
    # Proactively copy notifications to Syllabus folder as they contain the full syllabus
    logging.info("\n--- STEP 2: SYNCING SYLLABUS COPIES ---")
    notif_dir = BASE_DIR / "02_Notifications_&_Schedule"
    syllabus_dir = BASE_DIR / "01_Syllabus"
    syllabus_dir.mkdir(parents=True, exist_ok=True)
    for file in notif_dir.iterdir():
        if file.is_file() and file.name.startswith("Notice-CSE-"):
            dest = syllabus_dir / file.name
            if not dest.exists():
                shutil.copy2(str(file), str(dest))
                logging.info(f"   Copied CSE syllabus for year {file.name.split('-')[-1].split('.')[0]} to 01_Syllabus")

    logging.info("\n--- STEP 3: DOWNLOADING ANSWER KEYS ---")
    run_download_batch(ak_batch, "Answer Keys")
    
    logging.info("\n--- STEP 4: DOWNLOADING CUT-OFF MARKS ---")
    run_download_batch(co_batch, "Cut-off Marks")
    
    logging.info("\n--- STEP 5: DOWNLOADING CIVIL SERVICES PREVIOUS QUESTION PAPERS ---")
    run_download_batch(pyq_batch, "Previous Question Papers", workers=16)
    
    logging.info("\n🎉 All Done! UPSC Civil Services Resource Sync Completed Successfully.")

if __name__ == "__main__":
    main()
