#!/usr/bin/env python3
"""
UPSC Civil Services — ALL YEARS Previous Year Question Paper Downloader
=======================================================================
Strategy:
  1. Scrape every year's dedicated exam page on upsc.gov.in (2011-2026)
  2. Also scrape the main PYQ index page and archives page
  3. Classify each PDF into the correct subfolder
  4. Download with 16 parallel workers, skip-if-exists
"""

import re
import time
import urllib.parse
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE   = Path("UPSC_Resources/01_Civil_Services_IAS_IPS_IFS/03_Previous_Year_Papers")
LOG    = Path("UPSC_Resources/download_log_pyq.txt")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ── Classification rules (checked in order, case-insensitive on filename) ────
#  Returns a subfolder path relative to BASE
def classify(filename: str) -> str:
    u = filename.upper()

    # ── Prelims ──────────────────────────────────────────────────────────────
    # CSAT / GS-II (must be checked BEFORE generic GS-I)
    if re.search(r"CSP.*(?:CSAT|GS[- ]?II|PAPER[- ]?II|PAPER-2)|QP[- ]CSP.*GS-?II", u):
        return "Prelims/CSAT_Paper_2"
    if re.search(r"CSP.*(?:GS[- ]?I(?!I|V)|GENERAL.STUD.*PAPER[- ]?I(?!I|V)|PAPER[- ]?I(?!I|V))|QP[- ]CSP.*GS-?I(?!I|V)", u):
        return "Prelims/GS_Paper_1"
    # Generic prelims fallback
    if re.search(r"\bCSP\b.*(?:GENERAL.STUD|GS|PAPER)|PRELIM.*PAPER", u):
        return "Prelims/GS_Paper_1"

    # ── Mains ─────────────────────────────────────────────────────────────────
    if re.search(r"(?:CSM|QP.*CSM).*ESSAY|ESSAY.*(?:CSM|QP.*CSM)", u):
        return "Mains/Essay_Paper"

    if re.search(r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUD)[- ]?I(?!I|V)|"
                 r"(?:GS|GENERAL.STUD)[- ]?I(?!I|V).*(?:CSM|QP.*CSM)|"
                 r"GENERAL.STUDIES.PAPER[- ]?I(?!I|V).*CSM|CSM.*GENERAL.STUDIES.PAPER[- ]?I(?!I|V)|"
                 r"GS-?1.*CSM|CSM.*GS-?1", u):
        return "Mains/GS_Paper_1"

    if re.search(r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUD)[- ]?II(?!I)|"
                 r"(?:GS|GENERAL.STUD)[- ]?II(?!I).*(?:CSM|QP.*CSM)|"
                 r"GENERAL.STUDIES.PAPER[- ]?II(?!I).*CSM|CSM.*GENERAL.STUDIES.PAPER[- ]?II(?!I)|"
                 r"GS-?2.*CSM|CSM.*GS-?2", u):
        return "Mains/GS_Paper_2"

    if re.search(r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUD)[- ]?III|"
                 r"(?:GS|GENERAL.STUD)[- ]?III.*(?:CSM|QP.*CSM)|"
                 r"GENERAL.STUDIES.PAPER[- ]?III.*CSM|CSM.*GENERAL.STUDIES.PAPER[- ]?III|"
                 r"GS-?3.*CSM|CSM.*GS-?3", u):
        return "Mains/GS_Paper_3"

    if re.search(r"(?:CSM|QP.*CSM).*(?:GS|GENERAL.STUD)[- ]?IV|"
                 r"(?:GS|GENERAL.STUD)[- ]?IV.*(?:CSM|QP.*CSM)|"
                 r"ETHICS.*(?:CSM|QP.*CSM)|(?:CSM|QP.*CSM).*ETHICS|"
                 r"GENERAL.STUDIES.PAPER[- ]?IV.*CSM|CSM.*GENERAL.STUDIES.PAPER[- ]?IV|"
                 r"GS-?4.*CSM|CSM.*GS-?4", u):
        return "Mains/GS_Paper_4_Ethics"

    # IFS / Forest Service
    if re.search(r"IFSM|IFoS|FOREST.SERVICE|IFOS", u):
        return "Mains/IFS_Forest_Service"

    # Default → Optional Papers
    return "Mains/Optional_Papers"


# ── URL helpers ───────────────────────────────────────────────────────────────
def make_absolute(href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return "https://www.upsc.gov.in" + href
    return "https://www.upsc.gov.in/" + href


def is_civil_services_table(caption_text: str) -> bool:
    t = caption_text.lower()
    return "civil services" in t or "forest service" in t


def scrape_page(url: str) -> set[str]:
    """Return set of CSE/IFS PDF URLs found on the given page."""
    pdf_urls: set[str] = set()
    try:
        r = SESSION.get(url, timeout=20)
        if r.status_code != 200:
            return pdf_urls
        soup = BeautifulSoup(r.text, "html.parser")

        # Method 1: Tables with captions (PYQ index style)
        for table in soup.find_all("table"):
            cap = table.find("caption")
            cap_text = cap.get_text(strip=True) if cap else ""
            if not is_civil_services_table(cap_text):
                continue
            for a in table.find_all("a", href=re.compile(r"\.pdf$", re.I)):
                pdf_urls.add(make_absolute(a["href"]))

        # Method 2: Individual exam pages — grab ALL PDF links
        # (these pages list QPs directly without table captions)
        if not pdf_urls:
            for a in soup.find_all("a", href=re.compile(r"\.pdf$", re.I)):
                href = make_absolute(a["href"])
                fname = href.split("/")[-1].upper()
                # Only grab if it looks like a question paper (QP prefix, GS, Essay, etc.)
                if any(k in fname for k in [
                    "QP-CSP", "QP-CSM", "QP_CSP", "QP_CSM", "CSP-", "CSM-",
                    "GENERAL-STUDIES", "GENERAL_STUDIES", "GS-PAPER",
                    "ESSAY", "ENGLISH-COMP", "HINDI-COMP",
                    "IFSM", "QP-IFSM",
                ]):
                    pdf_urls.add(href)
    except Exception as e:
        print(f"  ⚠️  Error scraping {url}: {e}")
    return pdf_urls


# ── Main discovery ─────────────────────────────────────────────────────────────
def discover_all_pdfs() -> dict[str, str]:
    """Returns {pdf_url: subfolder} for all discovered CSE question papers."""
    all_urls: set[str] = set()

    # 1. Main PYQ index page + pagination
    print("📄 Scraping main PYQ index page (upsc.gov.in)...")
    for p in range(6):
        url = ("https://www.upsc.gov.in/examinations/previous-question-papers"
               if p == 0
               else f"https://www.upsc.gov.in/examinations/previous-question-papers?page={p}")
        found = scrape_page(url)
        all_urls.update(found)
        print(f"   Page {p}: {len(found)} PDFs (total {len(all_urls)})")
        time.sleep(0.3)

    # 2. Archives page
    print("📄 Scraping PYQ archives page...")
    arch = scrape_page("https://www.upsc.gov.in/examinations/previous-question-papers/archives")
    all_urls.update(arch)
    print(f"   Archives: {len(arch)} PDFs (total {len(all_urls)})")

    # 3. Individual year exam pages (2011–2026) — crucial for GS papers
    print("\n📅 Scraping individual year exam pages (2011–2026)...")
    for year in range(2011, 2027):
        year_found = set()
        pages = [
            f"Civil Services (Preliminary) Examination, {year}",
            f"Civil Services (Main) Examination, {year}",
            f"Civil Services Examination, {year}",
        ]
        for name in pages:
            url = "https://www.upsc.gov.in/examinations/" + urllib.parse.quote(name)
            found = scrape_page(url)
            year_found.update(found)
            time.sleep(0.15)
        all_urls.update(year_found)
        if year_found:
            print(f"   {year}: +{len(year_found)} PDFs (total {len(all_urls)})")
        else:
            print(f"   {year}: (none)")

    # Classify
    print(f"\n🗂️  Classifying {len(all_urls)} unique PDFs...")
    result = {}
    for url in all_urls:
        fname = urllib.parse.unquote(url.split("/")[-1])
        subfolder = classify(fname)
        result[url] = subfolder

    # Print distribution
    from collections import Counter
    dist = Counter(result.values())
    for folder, count in sorted(dist.items()):
        print(f"   {folder}: {count}")

    return result


# ── Downloader ─────────────────────────────────────────────────────────────────
def download(url: str, subfolder: str, retries: int = 3) -> dict:
    fname = urllib.parse.unquote(url.split("/")[-1])
    dest_dir = BASE / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / fname

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


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("   UPSC Civil Services — All-Years Previous Year Papers Downloader")
    print("=" * 70)

    url_map = discover_all_pdfs()
    total = len(url_map)
    print(f"\n🚀 Downloading {total} PDFs with 16 parallel workers...")
    print(f"📁 Destination: {BASE.resolve()}\n")

    stats = {"SUCCESS": 0, "SKIPPED": 0, "FAILED": 0, "NOT_FOUND": 0}
    completed = 0
    log_lines = []

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {
            executor.submit(download, url, subfolder): (url, subfolder)
            for url, subfolder in url_map.items()
        }
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

    # Final count per folder
    print("\n📂 Final file counts per subfolder:")
    for d in sorted(BASE.rglob("*")):
        if d.is_dir():
            count = len(list(d.glob("*.pdf")))
            if count > 0:
                rel = d.relative_to(BASE)
                print(f"   {rel}: {count} files")


if __name__ == "__main__":
    main()
