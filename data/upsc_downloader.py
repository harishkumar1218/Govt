#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║       UPSC CENTRAL GOVERNMENT EXAM RESOURCE DOWNLOADER v2       ║
║       Auto-scrapes www.upsc.gov.in for the latest PDFs          ║
╚══════════════════════════════════════════════════════════════════╝

Features:
  ✅ Auto-discovers ALL PDFs from the live UPSC website
  ✅ Smart categorization into proper exam folders
  ✅ Multi-threaded parallel downloads
  ✅ Skip-if-exists (resume interrupted downloads)
  ✅ Full summary report with log file
  ✅ Works with UPSC's URL patterns (www.upsc.gov.in)
"""

import os
import re
import time
import logging
import argparse
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────

BASE_URL   = "https://www.upsc.gov.in"
PYQ_PAGE   = f"{BASE_URL}/examinations/previous-question-papers"
SYLLABUS_PAGE = f"{BASE_URL}/examinations/syllabus-all"

BASE_DIR   = Path("UPSC_Resources")
LOG_FILE   = BASE_DIR / "download_log.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
    "Referer": BASE_URL,
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ─────────────────────────────────────────────────────────────────
# Smart Categorization Rules
# Maps filename keywords → (exam_folder, subfolder)
# ─────────────────────────────────────────────────────────────────

CATEGORY_RULES = [
    # Civil Services Prelims
    (r"CSP.*CSAT|CSP.*GS.*II|CSP.*PAPER.II|QP.CSP.*CSAT",
     "01_Civil_Services_IAS_IPS_IFS", "03_Previous_Year_Papers/Prelims/CSAT_Paper_2"),
    (r"CSP.*GS.*I(?!I|V)|CSP.*GENERAL.STUDIES.*PAPER.I(?!I|V)|QP.CSP.*GS-I(?!I|V)",
     "01_Civil_Services_IAS_IPS_IFS", "03_Previous_Year_Papers/Prelims/GS_Paper_1"),

    # Civil Services Mains
    (r"CSM.*ESSAY|IFSM.*ESSAY",
     "01_Civil_Services_IAS_IPS_IFS", "03_Previous_Year_Papers/Mains/Essay_Paper"),
    (r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUDIES).I(?!I|V)|(?:GS|GENERAL.STUDIES).I(?!I|V).*(?:CSM|QP.*CSM)",
     "01_Civil_Services_IAS_IPS_IFS", "03_Previous_Year_Papers/Mains/GS_Paper_1"),
    (r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUDIES).II(?!I)|(?:GS|GENERAL.STUDIES).II(?!I).*(?:CSM|QP.*CSM)",
     "01_Civil_Services_IAS_IPS_IFS", "03_Previous_Year_Papers/Mains/GS_Paper_2"),
    (r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUDIES).III|(?:GS|GENERAL.STUDIES).III.*(?:CSM|QP.*CSM)",
     "01_Civil_Services_IAS_IPS_IFS", "03_Previous_Year_Papers/Mains/GS_Paper_3"),
    (r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUDIES).IV|ETHICS.*(?:CSM|QP.*CSM)|(?:CSM|QP.*CSM).*ETHICS",
     "01_Civil_Services_IAS_IPS_IFS", "03_Previous_Year_Papers/Mains/GS_Paper_4_Ethics"),
    (r"CSM|IFoS.*MAINS|IFSM",
     "01_Civil_Services_IAS_IPS_IFS", "03_Previous_Year_Papers/Mains/Optional_Papers"),

    # NDA & NA
    (r"NDA.*MATH|NDA.*NA.*MATH",
     "02_NDA_NA", "03_Previous_Year_Papers/Maths"),
    (r"NDA.*GAT|NDA.*GENERAL.ABILITY",
     "02_NDA_NA", "03_Previous_Year_Papers/GAT_General_Ability"),
    (r"NDA",
     "02_NDA_NA", "03_Previous_Year_Papers/Other"),

    # CDS
    (r"CDS.*ENGLISH",
     "03_CDS", "03_Previous_Year_Papers/English"),
    (r"CDS.*GENERAL.KNOWLEDGE|CDS.*GK",
     "03_CDS", "03_Previous_Year_Papers/General_Knowledge"),
    (r"CDS.*MATH|CDS.*ELEMENTARY",
     "03_CDS", "03_Previous_Year_Papers/Mathematics"),
    (r"CDS",
     "03_CDS", "03_Previous_Year_Papers/Other"),

    # CAPF
    (r"CAPF.*PAPER.I|CAPF.*PAPER-I",
     "04_CAPF", "03_Previous_Year_Papers/Paper_1_GS"),
    (r"CAPF.*PAPER.II|CAPF.*PAPER-II",
     "04_CAPF", "03_Previous_Year_Papers/Paper_2_General_Ability"),
    (r"CAPF|CISF",
     "04_CAPF", "03_Previous_Year_Papers/Other"),

    # Engineering Services (ESE/IES)
    (r"ESPE.*GEN.STUD|ESPE.*ENGG.APTIT|ESE.*GS|ESE.*PRELIM",
     "08_Engineering_Services", "03_Previous_Year_Papers/Prelims"),
    (r"ESPE|ESE|IES.*ENGG",
     "08_Engineering_Services", "03_Previous_Year_Papers/Mains"),

    # Geo Scientist
    (r"CGSPE|GEO.SCI|GEO-SCI",
     "09_Geo_Scientist", "03_Previous_Year_Papers"),

    # Combined Medical Services
    (r"CMSE|CMS.*EXAM",
     "06_CMSE", "03_Previous_Year_Papers"),

    # SO/Steno
    (r"SO.*STENO|STENO.*SO|SO-\d+|LDCE.*SO|NOTING.*DRAFT",
     "10_SO_Steno", "03_Previous_Year_Papers"),

    # IES/ISS
    (r"IES.*STAT|ISS.*EXAM|ECONOMIC.SERVICE|STATISTICAL.SERVICE",
     "05_IES_ISS", "03_Previous_Year_Papers"),

    # IFS Mains (Indian Forest Service)
    (r"IFoS|IFSM|FOREST.SERVICE",
     "01_Civil_Services_IAS_IPS_IFS", "03_Previous_Year_Papers/Mains/IFS_Forest_Service"),

    # Syllabus files
    (r"Syllabus.*CSP|Syllabus.*Civil",
     "01_Civil_Services_IAS_IPS_IFS", "01_Syllabus"),
    (r"Syllabus.*NDA",
     "02_NDA_NA", "01_Syllabus"),
    (r"Syllabus.*CDS",
     "03_CDS", "01_Syllabus"),
    (r"Syllabus.*CAPF",
     "04_CAPF", "01_Syllabus"),
    (r"Syllabus.*CMSE|Syllabus.*Medical",
     "06_CMSE", "01_Syllabus"),
    (r"Syllabus.*IES|Syllabus.*ISS|Syllabus.*Economic|Syllabus.*Statistical",
     "05_IES_ISS", "01_Syllabus"),
    (r"Syllabus.*Engg|Syllabus.*Engineering",
     "08_Engineering_Services", "01_Syllabus"),
    (r"Syllabus.*Geo",
     "09_Geo_Scientist", "01_Syllabus"),
    (r"Syllabus",
     "99_Common_Resources", "Syllabi"),
]

DEFAULT_CATEGORY = ("99_Common_Resources", "Uncategorized")

# ─────────────────────────────────────────────────────────────────
# Folder Structure
# ─────────────────────────────────────────────────────────────────

FOLDER_STRUCTURE = {
    "01_Civil_Services_IAS_IPS_IFS": [
        "01_Syllabus",
        "02_Notifications_&_Schedule",
        "03_Previous_Year_Papers/Prelims/GS_Paper_1",
        "03_Previous_Year_Papers/Prelims/CSAT_Paper_2",
        "03_Previous_Year_Papers/Mains/GS_Paper_1",
        "03_Previous_Year_Papers/Mains/GS_Paper_2",
        "03_Previous_Year_Papers/Mains/GS_Paper_3",
        "03_Previous_Year_Papers/Mains/GS_Paper_4_Ethics",
        "03_Previous_Year_Papers/Mains/Essay_Paper",
        "03_Previous_Year_Papers/Mains/Optional_Papers",
        "03_Previous_Year_Papers/Mains/IFS_Forest_Service",
        "04_Answer_Keys",
        "05_Cut_Off_Marks",
        "06_Toppers_Copies",
        "07_Interview_Transcripts",
        "08_Study_Material",
    ],
    "02_NDA_NA": [
        "01_Syllabus",
        "02_Notifications_&_Schedule",
        "03_Previous_Year_Papers/Maths",
        "03_Previous_Year_Papers/GAT_General_Ability",
        "03_Previous_Year_Papers/Other",
        "04_Answer_Keys",
        "05_Cut_Off_Marks",
        "06_Study_Material",
    ],
    "03_CDS": [
        "01_Syllabus",
        "02_Notifications_&_Schedule",
        "03_Previous_Year_Papers/English",
        "03_Previous_Year_Papers/General_Knowledge",
        "03_Previous_Year_Papers/Mathematics",
        "03_Previous_Year_Papers/Other",
        "04_Answer_Keys",
        "05_Cut_Off_Marks",
        "06_Study_Material",
    ],
    "04_CAPF": [
        "01_Syllabus",
        "02_Notifications_&_Schedule",
        "03_Previous_Year_Papers/Paper_1_GS",
        "03_Previous_Year_Papers/Paper_2_General_Ability",
        "03_Previous_Year_Papers/Other",
        "04_Answer_Keys",
        "05_Cut_Off_Marks",
        "06_Study_Material",
    ],
    "05_IES_ISS": [
        "01_Syllabus", "02_Notifications_&_Schedule",
        "03_Previous_Year_Papers", "04_Answer_Keys", "05_Cut_Off_Marks",
    ],
    "06_CMSE": [
        "01_Syllabus", "02_Notifications_&_Schedule",
        "03_Previous_Year_Papers", "04_Answer_Keys", "05_Cut_Off_Marks",
    ],
    "07_CISF": [
        "01_Syllabus", "02_Notifications_&_Schedule",
        "03_Previous_Year_Papers", "04_Answer_Keys", "05_Cut_Off_Marks",
    ],
    "08_Engineering_Services": [
        "01_Syllabus", "02_Notifications_&_Schedule",
        "03_Previous_Year_Papers/Prelims",
        "03_Previous_Year_Papers/Mains",
        "04_Answer_Keys", "05_Cut_Off_Marks", "06_Study_Material",
    ],
    "09_Geo_Scientist": [
        "01_Syllabus", "02_Notifications_&_Schedule",
        "03_Previous_Year_Papers", "04_Answer_Keys", "05_Cut_Off_Marks",
    ],
    "10_SO_Steno": [
        "01_Syllabus", "02_Notifications_&_Schedule",
        "03_Previous_Year_Papers", "04_Answer_Keys",
    ],
    "99_Common_Resources": [
        "UPSC_Annual_Reports",
        "UPSC_Official_Notifications",
        "Syllabi",
        "Constitution_&_Acts",
        "NCERT_Books",
        "Government_Reports",
        "Current_Affairs",
        "Maps_&_Atlas",
        "Uncategorized",
    ],
}

# ─────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────

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

# ─────────────────────────────────────────────────────────────────
# Folder Creation
# ─────────────────────────────────────────────────────────────────

def create_folder_structure():
    logging.info("📁 Creating UPSC folder structure...")
    count = 0
    for exam, subfolders in FOLDER_STRUCTURE.items():
        exam_dir = BASE_DIR / exam
        exam_dir.mkdir(parents=True, exist_ok=True)
        for sf in subfolders:
            (exam_dir / sf).mkdir(parents=True, exist_ok=True)
            count += 1
    logging.info(f"✅ {count} folders ready.\n")

# ─────────────────────────────────────────────────────────────────
# Smart Categorizer
# ─────────────────────────────────────────────────────────────────

def categorize(filename: str) -> tuple[str, str]:
    """Return (exam_folder, subfolder) for a given PDF filename."""
    name_upper = filename.upper()
    for pattern, exam_folder, subfolder in CATEGORY_RULES:
        if re.search(pattern, name_upper, re.IGNORECASE):
            return exam_folder, subfolder
    return DEFAULT_CATEGORY

# ─────────────────────────────────────────────────────────────────
# Scraper: Collect all PDF URLs from UPSC website
# ─────────────────────────────────────────────────────────────────

def fetch_pdf_urls_from_page(url: str) -> list[str]:
    """Fetch all PDF hrefs from a given page URL."""
    try:
        resp = SESSION.get(url, timeout=20)
        resp.raise_for_status()
        urls = re.findall(r'href="([^"]*\.pdf)"', resp.text, re.IGNORECASE)
        # Make absolute
        result = []
        for u in urls:
            if u.startswith("http"):
                result.append(u)
            else:
                result.append(BASE_URL + u if u.startswith("/") else BASE_URL + "/" + u)
        return list(set(result))
    except Exception as e:
        logging.warning(f"⚠️  Could not fetch {url}: {e}")
        return []


def scrape_all_pdf_urls(pages: int = 5) -> list[str]:
    """Scrape PDF URLs from the UPSC PYQ page (multiple pages)."""
    logging.info("🔍 Scraping UPSC website for PDF links...")
    all_urls = set()

    # Previous Year Papers pages
    for page in range(pages):
        page_url = PYQ_PAGE if page == 0 else f"{PYQ_PAGE}?page={page}"
        logging.info(f"   📄 Scraping page {page}: {page_url}")
        urls = fetch_pdf_urls_from_page(page_url)
        all_urls.update(urls)
        logging.info(f"      Found {len(urls)} PDFs (total: {len(all_urls)})")
        time.sleep(0.5)

    # Syllabus page
    logging.info(f"   📄 Scraping syllabus page: {SYLLABUS_PAGE}")
    syllabus_urls = fetch_pdf_urls_from_page(SYLLABUS_PAGE)
    all_urls.update(syllabus_urls)
    logging.info(f"      Found {len(syllabus_urls)} syllabi (total: {len(all_urls)})")

    logging.info(f"\n✅ Total unique PDFs discovered: {len(all_urls)}\n")
    return list(all_urls)

# ─────────────────────────────────────────────────────────────────
# Downloader
# ─────────────────────────────────────────────────────────────────

def download_file(url: str, retries: int = 3) -> dict:
    """Download a single PDF and save it to the correct folder."""
    filename = url.split("/")[-1]
    exam_folder, subfolder = categorize(filename)
    dest_dir = BASE_DIR / exam_folder / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    if dest.exists() and dest.stat().st_size > 1024:
        return {"file": filename, "status": "SKIPPED", "path": str(dest)}

    for attempt in range(1, retries + 1):
        try:
            resp = SESSION.get(url, timeout=30, stream=True)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "")
                if "html" in content_type and "pdf" not in content_type:
                    return {"file": filename, "status": "FAILED",
                            "reason": "Got HTML instead of PDF", "url": url}

                downloaded = 0
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=16384):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                return {
                    "file": filename,
                    "status": "SUCCESS",
                    "size_kb": round(downloaded / 1024, 1),
                    "path": str(dest),
                    "category": f"{exam_folder}/{subfolder}",
                }
            elif resp.status_code == 404:
                return {"file": filename, "status": "NOT_FOUND", "url": url}
            else:
                if attempt < retries:
                    time.sleep(2 * attempt)
                else:
                    return {"file": filename, "status": "FAILED",
                            "reason": f"HTTP {resp.status_code}", "url": url}

        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(3 * attempt)
            else:
                return {"file": filename, "status": "FAILED", "reason": "Timeout", "url": url}
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                return {"file": filename, "status": "FAILED", "reason": str(e), "url": url}

    return {"file": filename, "status": "FAILED", "reason": "Max retries", "url": url}


def download_all(urls: list[str], max_workers: int = 4) -> dict:
    total = len(urls)
    logging.info(f"🚀 Downloading {total} PDFs with {max_workers} workers...\n")

    results = {"SUCCESS": [], "SKIPPED": [], "FAILED": [], "NOT_FOUND": []}
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_file, url): url for url in urls}

        for future in as_completed(futures):
            completed += 1
            result = future.result()
            status = result["status"]
            results[status].append(result)

            icons = {"SUCCESS": "✅", "SKIPPED": "⏭️", "FAILED": "❌", "NOT_FOUND": "🔍"}
            icon = icons.get(status, "?")
            msg = f"[{completed:>4}/{total}] {icon} {result['file']}"
            if status == "SUCCESS":
                msg += f"  →  {result.get('category', '')}  ({result.get('size_kb', 0)} KB)"
            elif status in ("FAILED", "NOT_FOUND"):
                msg += f"  — {result.get('reason', '')}"
            logging.info(msg)

    return results

# ─────────────────────────────────────────────────────────────────
# Summary Report
# ─────────────────────────────────────────────────────────────────

def print_summary(results: dict, total_scraped: int):
    total = sum(len(v) for v in results.values())
    success = len(results["SUCCESS"])
    skipped = len(results["SKIPPED"])
    failed  = len(results["FAILED"]) + len(results["NOT_FOUND"])
    total_kb = sum(r.get("size_kb", 0) for r in results["SUCCESS"])

    report = f"""
╔══════════════════════════════════════════════════════════════╗
║             UPSC RESOURCE DOWNLOADER — FINAL REPORT         ║
╠══════════════════════════════════════════════════════════════╣
║  🔍 PDFs Discovered (scraped)  : {total_scraped:<27}║
║  📦 Total Processed            : {total:<27}║
║  ✅ Successfully Downloaded    : {success:<27}║
║  ⏭️  Skipped (already exists)   : {skipped:<27}║
║  ❌ Failed / Not Found         : {failed:<27}║
║  💾 Total Data Downloaded      : {f"{total_kb/1024:.2f} MB":<27}║
╠══════════════════════════════════════════════════════════════╣
║  📁 Output Directory  : {str(BASE_DIR):<37}║
║  📄 Log File          : {str(LOG_FILE):<37}║
╚══════════════════════════════════════════════════════════════╝
"""
    print(report)
    logging.info(report)

    # Per-folder stats
    folder_counts = {}
    for r in results["SUCCESS"]:
        cat = r.get("category", "Unknown")
        folder_counts[cat] = folder_counts.get(cat, 0) + 1

    if folder_counts:
        logging.info("📂 Files per category:")
        for cat, count in sorted(folder_counts.items()):
            logging.info(f"   {count:>4} × {cat}")

# ─────────────────────────────────────────────────────────────────
# Tree Printer
# ─────────────────────────────────────────────────────────────────

def print_tree(directory: Path, prefix: str = "", max_depth: int = 4, depth: int = 0):
    if depth > max_depth:
        return
    items = sorted(directory.iterdir())
    for i, item in enumerate(items):
        connector = "└── " if i == len(items) - 1 else "├── "
        if item.is_dir():
            # Count PDFs in this dir (recursive)
            pdf_count = len(list(item.rglob("*.pdf")))
            label = f"📁 {item.name}/" + (f"  [{pdf_count} PDFs]" if pdf_count else "")
            print(f"{prefix}{connector}{label}")
            ext = "    " if i == len(items) - 1 else "│   "
            print_tree(item, prefix + ext, max_depth, depth + 1)
        else:
            size = item.stat().st_size
            size_str = f"{size/1024:.0f}KB" if size > 1024 else f"{size}B"
            print(f"{prefix}{connector}📄 {item.name}  ({size_str})")

# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UPSC Central Government Exam Resource Downloader v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python upsc_downloader.py                         # Scrape + download all
  python upsc_downloader.py --pages 10              # Scrape 10 pages of PYQs
  python upsc_downloader.py --structure-only        # Only create folders
  python upsc_downloader.py --tree                  # Show folder tree
  python upsc_downloader.py --workers 6             # 6 parallel downloads
  python upsc_downloader.py --output-dir ~/Desktop/UPSC
        """,
    )
    parser.add_argument("--structure-only", action="store_true",
                        help="Only create folder structure, skip downloads")
    parser.add_argument("--tree", action="store_true",
                        help="Show folder/file tree after completion")
    parser.add_argument("--workers", type=int, default=4,
                        help="Parallel download threads (default: 4)")
    parser.add_argument("--pages", type=int, default=5,
                        help="Number of PYQ website pages to scrape (default: 5)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Custom output directory (default: ./UPSC_Resources)")

    args = parser.parse_args()

    global BASE_DIR, LOG_FILE
    if args.output_dir:
        BASE_DIR = Path(args.output_dir)
        LOG_FILE = BASE_DIR / "download_log.txt"

    setup_logging()

    logging.info("=" * 64)
    logging.info("   UPSC CENTRAL GOVERNMENT EXAM RESOURCE DOWNLOADER v2")
    logging.info(f"   Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"   Output  : {BASE_DIR.resolve()}")
    logging.info("=" * 64 + "\n")

    # Step 1: Create folder structure
    create_folder_structure()

    if args.structure_only:
        logging.info("✅ Folder structure created. Exiting (--structure-only).")
    else:
        # Step 2: Scrape all PDF URLs from UPSC website
        all_pdf_urls = scrape_all_pdf_urls(pages=args.pages)

        if not all_pdf_urls:
            logging.error("❌ No PDFs found. Check network connectivity.")
            return

        # Step 3: Download
        results = download_all(all_pdf_urls, max_workers=args.workers)

        # Step 4: Summary
        print_summary(results, len(all_pdf_urls))

    # Step 5: Optional tree
    if args.tree:
        print(f"\n📂 UPSC Resources Tree ({BASE_DIR.resolve()})\n")
        print_tree(BASE_DIR)

    logging.info(f"\n🎉 All done! Open: {BASE_DIR.resolve()}")


if __name__ == "__main__":
    main()
