import uuid
from django.db import models
from django.contrib.auth.models import User

class EssayPracticeSession(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
    ]
    
    user = models.ForeignKey(User, related_name='essay_sessions', on_delete=models.CASCADE)
    track_slug = models.CharField(max_length=100)
    roadmap_item_id = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class EssayQuestion(models.Model):
    session = models.ForeignKey(EssayPracticeSession, related_name='questions', on_delete=models.CASCADE)
    prompt_text = models.TextField()
    order = models.PositiveIntegerField(default=1)
    max_marks = models.IntegerField(default=125)
    upload_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order} - {self.session.title}"

class EssayAnswerImage(models.Model):
    question = models.ForeignKey(EssayQuestion, related_name='images', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='essay_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='essay_answers/%Y/%m/')
    page_number = models.PositiveIntegerField(default=1)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['question', 'page_number', 'uploaded_at']

    def __str__(self):
        return f"Image for {self.question} - Page {self.page_number}"

class EssayReview(models.Model):
    session = models.OneToOneField(EssayPracticeSession, related_name='review', on_delete=models.CASCADE)
    reviewer = models.ForeignKey(User, related_name='given_reviews', null=True, blank=True, on_delete=models.SET_NULL)
    marks_awarded = models.FloatField(default=0.0)
    feedback = models.TextField()
    rubric = models.JSONField(default=dict, blank=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.session}"

class EssayOCRPage(models.Model):
    answer_image = models.OneToOneField(EssayAnswerImage, related_name='ocr_page', on_delete=models.CASCADE)
    extracted_text = models.TextField(blank=True)
    confidence_score = models.FloatField(default=0.0)
    image_quality_flags = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OCR for {self.answer_image}"

class EssayAnswerTranscript(models.Model):
    EXTRACTION_QUALITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    question = models.OneToOneField(EssayQuestion, related_name='transcript', on_delete=models.CASCADE)
    session = models.ForeignKey(EssayPracticeSession, related_name='transcripts', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='essay_transcripts', on_delete=models.CASCADE)
    combined_text = models.TextField(blank=True)
    word_count = models.PositiveIntegerField(default=0)
    detected_language = models.CharField(max_length=50, default='en')
    extraction_quality = models.CharField(max_length=20, choices=EXTRACTION_QUALITY_CHOICES, default='medium')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transcript for {self.question}"

class EssayAIReview(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    RATING_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('weak', 'Weak'),
        ('poor', 'Poor'),
    ]
    session = models.ForeignKey(EssayPracticeSession, related_name='ai_reviews', on_delete=models.CASCADE)
    question = models.OneToOneField(EssayQuestion, related_name='ai_review', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='ai_essay_reviews', on_delete=models.CASCADE)
    transcript = models.OneToOneField(EssayAnswerTranscript, related_name='ai_review', on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_score = models.FloatField(default=0.0)
    max_score = models.IntegerField(default=125)
    percentage = models.FloatField(default=0.0)
    rating_band = models.CharField(max_length=20, choices=RATING_CHOICES, default='average')
    
    review_json = models.JSONField(default=dict, blank=True)
    strengths = models.JSONField(default=list, blank=True)
    weaknesses = models.JSONField(default=list, blank=True)
    suggestions = models.JSONField(default=list, blank=True)
    retrieved_context = models.JSONField(default=list, blank=True)
    
    model_name = models.CharField(max_length=100, default='mock_evaluator_v1')
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AI Review for {self.question} - {self.status}"
