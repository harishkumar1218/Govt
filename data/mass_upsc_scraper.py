import requests
from bs4 import BeautifulSoup
import urllib3
import json
import os
import re

urllib3.disable_warnings()

# Configuration
URLS = [
    'https://www.upsc.gov.in/examinations/previous-question-papers',
    'https://www.upsc.gov.in/examinations/previous-question-papers/archives',
    'https://www.upsc.gov.in/examinations/answer-key',
    'https://www.upsc.gov.in/examinations/answer-key/archives',
    'https://www.upsc.gov.in/examinations/active-exams',
    'https://www.upsc.gov.in/examinations/forthcoming-exams'
]

def categorize_exam(title, url_href):
    text = (title + " " + url_href).lower()
    
    if 'civil service' in text or 'csp' in text or 'csm' in text or 'ias' in text:
        return '01_Civil_Services'
    elif 'nda' in text or 'naval academy' in text:
        return '02_NDA_NA'
    elif 'cds' in text or 'combined defence' in text:
        return '03_CDS'
    elif 'engineering' in text or 'ese' in text:
        return '04_Engineering_Services'
    elif 'medical' in text or 'cms' in text:
        return '05_Medical_Services'
    elif 'geologist' in text or 'geo-scientist' in text:
        return '06_Geo_Scientist'
    elif 'capf' in text or 'central armed' in text:
        return '07_CAPF'
    elif 'cisf' in text:
        return '08_CISF'
    elif 'forest' in text or 'ifs' in text or 'ifos' in text:
        return '09_Forest_Service'
    elif 'ies' in text or 'iss' in text or 'economic' in text or 'statistical' in text:
        return '10_IES_ISS'
    elif 'so-steno' in text or 'steno' in text:
        return '11_SO_Steno'
    else:
        return '12_Other_Exams'
        
def get_pdf_category(source_url):
    if 'previous-question-papers' in source_url:
        return 'Previous_Year_Papers'
    elif 'answer-key' in source_url:
        return 'Answer_Keys'
    elif 'active-exams' in source_url or 'forthcoming-exams' in source_url:
        return 'Syllabus_Notifications'
    else:
        return 'Misc'

def run_dry_run():
    all_pdfs = []
    
    print("Gathering PDF links across UPSC...")
    for base_url in URLS:
        print(f"Scanning {base_url}...")
        for page in range(30): # check up to 30 pages
            url = f'{base_url}?page={page}' if page > 0 else base_url
            try:
                r = requests.get(url, verify=False, timeout=10)
                if r.status_code != 200:
                    break
                soup = BeautifulSoup(r.text, 'html.parser')
                links = [a for a in soup.find_all('a', href=True) if '.pdf' in a['href'].lower()]
                
                if not links and page > 1:
                    break
                    
                category = get_pdf_category(base_url)
                
                for a in links:
                    title = a.get_text().strip()
                    # Many links just show file size like "(1.5 MB)", so we get parent row text
                    if not title or len(title) < 15:
                        parent_row = a.find_parent('tr')
                        if parent_row:
                            title = parent_row.get_text(" ").strip()
                            title = re.sub(r'\s+', ' ', title)
                            
                    href = a['href']
                    if not href.startswith('http'):
                        href = 'https://www.upsc.gov.in' + href
                        
                    exam_folder = categorize_exam(title, href)
                    
                    all_pdfs.append({
                        "source_url": base_url,
                        "title": title,
                        "pdf_url": href,
                        "exam_folder": exam_folder,
                        "category": category
                    })
                    
            except Exception as e:
                print(f"Error on {url}: {e}")
                break
                
    # Save the dry run map
    out_file = '/Users/harish/Public/Govt/data/dry_run_map.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(all_pdfs, f, indent=4)
        
    print(f"Dry run complete. Found {len(all_pdfs)} PDFs.")
    print(f"Mapping saved to {out_file}")
    
    # Print summary
    summary = {}
    for item in all_pdfs:
        folder = item['exam_folder']
        summary[folder] = summary.get(folder, 0) + 1
        
    print("\nCategorization Summary:")
    for k, v in sorted(summary.items()):
        print(f"  {k}: {v} PDFs")

if __name__ == "__main__":
    run_dry_run()
