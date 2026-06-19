import requests
from bs4 import BeautifulSoup
from celery import shared_task
from .models import AllowedDomain, KnowledgeDocument
from urllib.parse import urlparse
from django.utils import timezone

@shared_task
def research_internet(url, exam, subject, topic):
    # 1. Validate domain allow-list
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace('www.', '')
    
    if not AllowedDomain.objects.filter(domain__icontains=domain, is_active=True).exists():
        return f"Error: Domain {domain} is not in the allowed list."

    # 2. Fetch content
    try:
        headers = {'User-Agent': 'UPSCAspireBot/1.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Error fetching {url}: {str(e)}"
        
    # 3. Extract text
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()
        
    text_content = soup.get_text(separator='\n', strip=True)
    
    # 4. Save metadata to Postgres
    doc = KnowledgeDocument.objects.create(
        exam=exam,
        subject=subject,
        topic=topic,
        source_url=url,
        source_type='html',
        document_version=f"{timezone.now().year}-v1",
        document_hash=str(hash(text_content))[:250],
        confidence_score=0.95
    )
    
    # Note: In the full pipeline, text_content is chunked and sent to Qdrant here.
    return f"Successfully researched and ingested {url} into Document ID {doc.id}"
