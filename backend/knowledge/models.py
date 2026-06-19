import uuid
from django.db import models

class KnowledgeDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.CharField(max_length=100)
    stage = models.CharField(max_length=100, blank=True)
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)
    subtopic = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    source_type = models.CharField(max_length=50) # 'official_pdf', 'html', etc.
    publication_date = models.DateField(null=True, blank=True)
    ingestion_date = models.DateTimeField(auto_now_add=True)
    document_version = models.CharField(max_length=50)
    confidence_score = models.FloatField(default=1.0)
    document_hash = models.CharField(max_length=256, unique=True)
    
    def __str__(self):
        return f"[{self.exam}] {self.subject} - {self.topic} ({self.document_version})"

class AllowedDomain(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    priority_level = models.IntegerField(default=1) # 1 = Highest
    
    def __str__(self):
        return self.domain
