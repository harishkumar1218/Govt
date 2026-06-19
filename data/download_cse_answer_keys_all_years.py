#!/usr/bin/env python3
"""
UPSC Civil Services — ALL YEARS Answer Keys Downloader
======================================================
Strategy:
  1. Scrape the main Answer Key page and its archives
  2. Scrape individual year's exam pages
  3. Classify and download the answer keys into 04_Answer_Keys
"""

import re
import time
import urllib.parse
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = Path("UPSC_Resources/01_Civil_Services_IAS_IPS_IFS/04_Answer_Keys")
BASE.mkdir(parents=True, exist_ok=True)
LOG = Path("UPSC_Resources/download_log_ak.txt")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

def make_absolute(href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return "https://www.upsc.gov.in" + href
    return "https://www.upsc.gov.in/" + href

def is_civil_services(text: str) -> bool:
    t = text.lower()
    return "civil services" in t

def scrape_page(url: str, is_individual_page: bool = False) -> set[str]:
    pdf_urls: set[str] = set()
    try:
        r = SESSION.get(url, timeout=20)
        if r.status_code != 200:
            return pdf_urls
        soup = BeautifulSoup(r.text, "html.parser")

        # Table caption method
        for table in soup.find_all("table"):
            cap = table.find("caption")
            cap_text = cap.get_text(strip=True) if cap else ""
            if not is_civil_services(cap_text) and not is_individual_page:
                continue
            for a in table.find_all("a", href=re.compile(r"\.pdf$", re.I)):
                href = make_absolute(a["href"])
                if 'ans' in href.lower() or 'key' in href.lower():
                    pdf_urls.add(href)

        # Non-table links (for individual pages)
        if is_individual_page:
            for a in soup.find_all("a", href=re.compile(r"\.pdf$", re.I)):
                href = make_absolute(a["href"])
                text = a.get_text(strip=True).lower()
                fname = href.split("/")[-1].lower()
                if 'ans' in fname or 'key' in fname or 'ans' in text or 'key' in text:
                    pdf_urls.add(href)

    except Exception as e:
        print(f"  ⚠️  Error scraping {url}: {e}")
    return pdf_urls

def discover_all_pdfs() -> set[str]:
    all_urls: set[str] = set()

    print("📄 Scraping main Answer Key index page...")
    for p in range(5):
        url = ("https://www.upsc.gov.in/examinations/answer-key"
               if p == 0
               else f"https://www.upsc.gov.in/examinations/answer-key?page={p}")
        found = scrape_page(url)
        all_urls.update(found)
        print(f"   Page {p}: {len(found)} PDFs (total {len(all_urls)})")
        time.sleep(0.3)

    print("📄 Scraping Answer Key archives page...")
    # There could be multiple pages in archive
    for p in range(5):
        url = ("https://www.upsc.gov.in/examinations/answer-key/archives"
               if p == 0
               else f"https://www.upsc.gov.in/examinations/answer-key/archives?page={p}")
        found = scrape_page(url)
        all_urls.update(found)
        print(f"   Archive Page {p}: {len(found)} PDFs (total {len(all_urls)})")
        time.sleep(0.3)

    print("\n📅 Scraping individual year exam pages (2011–2026)...")
    for year in range(2011, 2027):
        year_found = set()
        pages = [
            f"Civil Services (Preliminary) Examination, {year}",
            f"Civil Services Examination, {year}",
        ]
        for name in pages:
            url = "https://www.upsc.gov.in/examinations/" + urllib.parse.quote(name)
            found = scrape_page(url, is_individual_page=True)
            year_found.update(found)
            time.sleep(0.15)
        all_urls.update(year_found)
        if year_found:
            print(f"   {year}: +{len(year_found)} PDFs (total {len(all_urls)})")
        else:
            print(f"   {year}: (none)")

    return all_urls

def download(url: str, retries: int = 3) -> dict:
    fname = urllib.parse.unquote(url.split("/")[-1])
    # Add year to filename if possible to avoid collisions, but let's just use original name if it's unique
    dest_path = BASE / fname

    if dest_path.exists() and dest_path.stat().st_size > 1024:
        return {"file": fname, "status": "SKIPPED"}

    for attempt in range(1, retries + 1):
        try:
            r = SESSION.get(url, timeout=45, stream=True)
            if r.status_code == 200:
                ct = r.headers.get("Content-Type", "")
                if "html" in ct and "pdf" not in ct:
                    return {"file": fname, "status": "FAILED", "reason": "HTML response"}
                downloaded = 0
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(16384):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                return {"file": fname, "status": "SUCCESS", "kb": round(downloaded / 1024, 1)}
            elif r.status_code == 404:
                return {"file": fname, "status": "NOT_FOUND", "url": url}
            else:
                if attempt < retries:
                    time.sleep(2 * attempt)
        except Exception as e:
            if attempt < retries:
                time.sleep(2 * attempt)
            else:
                return {"file": fname, "status": "FAILED", "reason": str(e)}

    return {"file": fname, "status": "FAILED", "reason": "Max retries"}

def main():
    print("=" * 70)
    print("   UPSC Civil Services — All-Years Answer Keys Downloader")
    print("=" * 70)

    url_set = discover_all_pdfs()
    
    # Add known hardcoded URLs that might be missing from direct pages
    hardcoded = [
        "https://www.upsc.gov.in/sites/default/files/CSP_2016_GS_I.pdf",
        "https://www.upsc.gov.in/sites/default/files/CSP_2016_GS_II.pdf",
        "https://www.upsc.gov.in/sites/default/files/CSP_2017_GS_Paper-1_0.pdf",
        "https://www.upsc.gov.in/sites/default/files/CSP_2017_GS_Paper-2_0.pdf",
        "https://www.upsc.gov.in/sites/default/files/CSP_18_GS_Paper_I_C.pdf",
        "https://www.upsc.gov.in/sites/default/files/CSP_18_GS_Paper_II_C.pdf",
        "https://www.upsc.gov.in/sites/default/files/Answer-Key-CSP-19-GS-I.pdf",
        "https://www.upsc.gov.in/sites/default/files/Answer-Key-CSP-19-GS-II.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2020-GS-I.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-2020-GS-II.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-21-GS1-100622.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSPE-21-GS2-100622.pdf",
        "https://www.upsc.gov.in/sites/default/files/Ans-Key-CSP-22-GS-I-220623.pdf",
        "https://www.upsc.gov.in/sites/default/files/Ans-Key-CSP-22-GS-II-220623.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSP-23-GS-I-080524.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSP-23-GS-II-080524.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSP-24-GS-I-301024.pdf",
        "https://www.upsc.gov.in/sites/default/files/AnsKey-CSP-24-GS-II-301024.pdf"
    ]
    url_set.update(hardcoded)

    total = len(url_set)
    print(f"\n🚀 Downloading {total} PDFs with 16 parallel workers...")
    print(f"📁 Destination: {BASE.resolve()}\n")

    stats = {"SUCCESS": 0, "SKIPPED": 0, "FAILED": 0, "NOT_FOUND": 0}
    completed = 0
    log_lines = []

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(download, url): url for url in url_set}
        for future in as_completed(futures):
            completed += 1
            res = future.result()
            status = res["status"]
            stats[status] = stats.get(status, 0) + 1
            icon = {"SUCCESS": "✅", "SKIPPED": "⏭️ ", "FAILED": "❌", "NOT_FOUND": "🔍"}.get(status, "?")
            msg = f"[{completed:>4}/{total}] {icon} {res['file']} → {status}"
            if status == "SUCCESS":
                msg += f" ({res.get('kb', 0)} KB)"
            elif status in ("FAILED", "NOT_FOUND"):
                msg += f" | {res.get('reason', res.get('url', ''))}"
            print(msg)
            log_lines.append(msg)

    LOG.write_text("\n".join(log_lines), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"📊 Summary: ✅ {stats['SUCCESS']} downloaded  ⏭️  {stats['SKIPPED']} skipped  "
          f"❌ {stats['FAILED']} failed  🔍 {stats['NOT_FOUND']} not found")
    print("=" * 70)

if __name__ == "__main__":
    main()
