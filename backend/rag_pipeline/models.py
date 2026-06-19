import uuid
from django.db import models
from knowledge.models import KnowledgeDocument

class MockTest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.CharField(max_length=100)
    target_date = models.DateField()
    questions = models.JSONField(default=list) # List of UUIDs or embedded data
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.exam} Mock Test for {self.target_date}"

class GeneratedQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)
    question_text = models.TextField()
    options = models.JSONField() # {"A": "...", "B": "..."}
    correct_answer = models.CharField(max_length=1)
    explanation = models.TextField()
    passed_qa = models.BooleanField(default=False)
    difficulty = models.FloatField(default=1.0)
    source_document = models.ForeignKey(KnowledgeDocument, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.exam} - {self.topic} (QA: {self.passed_qa})"
