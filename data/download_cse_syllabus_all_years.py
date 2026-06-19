#!/usr/bin/env python3
"""
Download UPSC Civil Services Examination notification PDFs for ALL years.
These notification PDFs contain the complete official syllabus for each year.

Strategy:
  1. Scrape each year's dedicated exam page on upsc.gov.in
  2. Extract notification / notice PDF links
  3. Download to 01_Syllabus/ with a descriptive year-prefixed filename
"""

import re
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

DEST = Path("UPSC_Resources/01_Civil_Services_IAS_IPS_IFS/01_Syllabus")
DEST.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ── Year → UPSC exam page URL patterns ────────────────────────────────────────
# UPSC hosts each year's page at:
#   /examinations/Civil Services (Preliminary) Examination, <YEAR>
#   /examinations/Civil Services Examination, <YEAR>   (combined page for some years)

def build_exam_urls(year: int) -> list[str]:
    """Return all candidate URLs for a given year's CSE page."""
    base = "https://www.upsc.gov.in/examinations/"
    import urllib.parse
    names = [
        f"Civil Services (Preliminary) Examination, {year}",
        f"Civil Services Examination, {year}",
        f"Civil Services (Main) Examination, {year}",
    ]
    return [base + urllib.parse.quote(n) for n in names]


def scrape_notification_pdfs(year: int) -> list[tuple[str, str]]:
    """
    Scrape the UPSC exam page for a given year and return
    (pdf_url, suggested_filename) tuples for notification/notice PDFs.
    """
    results = []
    seen_urls = set()

    for url in build_exam_urls(year):
        try:
            r = SESSION.get(url, timeout=20)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if not href.lower().endswith(".pdf"):
                    continue
                # Only grab notification / notice / corrigendum / instruction PDFs
                lowpath = href.lower()
                if not any(kw in lowpath for kw in ["notif", "notice", "instruction", "corrig"]):
                    continue
                # Must be CSP / CSE / civil-services related
                if not any(kw in lowpath for kw in ["csp", "cse", "cs-", "civil"]):
                    # Allow if text suggests it
                    if not any(kw in text.lower() for kw in ["notice", "notif", "instruction"]):
                        continue
                if not href.startswith("http"):
                    href = "https://www.upsc.gov.in" + href
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # Build a clean destination filename
                raw_name = href.split("/")[-1]
                # Strip URL encoding
                import urllib.parse
                raw_name = urllib.parse.unquote(raw_name)
                dest_name = f"CSE_{year}_{raw_name}"
                results.append((href, dest_name))
        except Exception as e:
            print(f"  ⚠️  Error scraping {url}: {e}")
        time.sleep(0.2)

    return results


def download(url: str, dest_path: Path, retries: int = 3) -> dict:
    filename = dest_path.name
    if dest_path.exists() and dest_path.stat().st_size > 1024:
        return {"file": filename, "status": "SKIPPED"}
    for attempt in range(1, retries + 1):
        try:
            r = SESSION.get(url, timeout=60, stream=True)
            if r.status_code == 200:
                ct = r.headers.get("Content-Type", "")
                if "html" in ct and "pdf" not in ct:
                    return {"file": filename, "status": "FAILED", "reason": "HTML response"}
                downloaded = 0
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(16384):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                return {"file": filename, "status": "SUCCESS", "kb": round(downloaded / 1024, 1)}
            elif r.status_code == 404:
                return {"file": filename, "status": "NOT_FOUND", "url": url}
            else:
                if attempt < retries:
                    time.sleep(2 * attempt)
        except Exception as e:
            if attempt < retries:
                time.sleep(2 * attempt)
            else:
                return {"file": filename, "status": "FAILED", "reason": str(e)}
    return {"file": filename, "status": "FAILED", "reason": "Max retries"}


def main():
    print("=" * 68)
    print("  UPSC Civil Services — All-Years Syllabus (Notification) Downloader")
    print("=" * 68)

    all_downloads: list[tuple[str, Path]] = []

    # Discover: scrape every year's page
    print("\n🔍 Discovering notification PDFs for 2011–2026...")
    for year in range(2011, 2027):
        pdfs = scrape_notification_pdfs(year)
        if pdfs:
            print(f"  {year}: {len(pdfs)} PDF(s) found")
            for url, name in pdfs:
                all_downloads.append((url, DEST / name))
        else:
            print(f"  {year}: (no notification PDFs found via scrape)")

    # Hardcoded fallbacks for years whose pages are missing / return 404
    # These are verified URLs from prior research (older format)
    FALLBACKS = {
        # Format: year → [(url, filename)]
        2020: [
            ("https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2020_Engl_120220.pdf",
             "CSE_2020_Notice-CS(P)E-2020_Engl_120220.pdf"),
        ],
        2021: [
            ("https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2021_Engl_040321.pdf",
             "CSE_2021_Notice-CS(P)E-2021_Engl_040321.pdf"),
        ],
        2022: [
            ("https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2022_Engl_020222.pdf",
             "CSE_2022_Notice-CS(P)E-2022_Engl_020222.pdf"),
        ],
        2023: [
            ("https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2023_Engl_010223.pdf",
             "CSE_2023_Notice-CS(P)E-2023_Engl_010223.pdf"),
        ],
        2024: [
            ("https://www.upsc.gov.in/sites/default/files/Notice-CS%28P%29E-2024_Engl_140224.pdf",
             "CSE_2024_Notice-CS(P)E-2024_Engl_140224.pdf"),
        ],
    }

    existing_urls = {url for url, _ in all_downloads}
    for year, entries in FALLBACKS.items():
        for url, name in entries:
            # Add only if not already discovered
            if url not in existing_urls and (DEST / name).stat().st_size < 1024 if (DEST / name).exists() else True:
                all_downloads.append((url, DEST / name))
                existing_urls.add(url)
                print(f"  {year}: added fallback → {name}")

    # Remove duplicates by dest path
    seen_paths = set()
    unique_downloads = []
    for url, path in all_downloads:
        if str(path) not in seen_paths:
            seen_paths.add(str(path))
            unique_downloads.append((url, path))

    print(f"\n📥 Total files to download (new): {len(unique_downloads)}")
    print(f"📁 Destination: {DEST.resolve()}\n")

    # Download in parallel
    stats = {"SUCCESS": 0, "SKIPPED": 0, "FAILED": 0, "NOT_FOUND": 0}
    total = len(unique_downloads)
    completed = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(download, url, path): (url, path) for url, path in unique_downloads}
        for future in as_completed(futures):
            completed += 1
            res = future.result()
            status = res["status"]
            stats[status] = stats.get(status, 0) + 1
            icon = {"SUCCESS": "✅", "SKIPPED": "⏭️", "FAILED": "❌", "NOT_FOUND": "🔍"}.get(status, "?")
            msg = f"[{completed:>3}/{total}] {icon} {res['file']} → {status}"
            if status == "SUCCESS":
                msg += f" ({res.get('kb', 0)} KB)"
            elif status == "FAILED":
                msg += f" ({res.get('reason', '')})"
            print(msg)

    print(f"\n📊 Summary: Success={stats['SUCCESS']}, Skipped={stats['SKIPPED']}, "
          f"Failed={stats['FAILED']}, Not Found={stats['NOT_FOUND']}")

    # Final listing
    print(f"\n📂 Contents of {DEST}:")
    files = sorted(DEST.glob("*.pdf"))
    for f in files:
        print(f"  {f.name}  ({round(f.stat().st_size / 1024, 1)} KB)")
    print(f"\n  Total: {len(files)} file(s)")


if __name__ == "__main__":
    main()
