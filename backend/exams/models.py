from django.db import models

class ExamTrack(models.Model):
    slug = models.SlugField(primary_key=True, max_length=100)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200)
    description = models.TextField()
    gradient = models.CharField(max_length=200)

    def __str__(self):
        return self.title

class ExamPattern(models.Model):
    track = models.ForeignKey(ExamTrack, related_name='patterns', on_delete=models.CASCADE)
    stage_name = models.CharField(max_length=200)
    total_questions = models.PositiveIntegerField()
    duration_seconds = models.PositiveIntegerField()
    marks_per_question = models.FloatField()
    negative_marking = models.FloatField()
    source_url = models.URLField(blank=True, null=True)
    last_verified = models.DateField(auto_now=True)

    def __str__(self):
        return f"{self.track.slug} - {self.stage_name} Pattern"

class ExamStage(models.Model):
    track = models.ForeignKey(ExamTrack, related_name='flowchart', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=200)
    stage_type = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    description = models.TextField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.track.slug} - {self.title}"

class SyllabusSection(models.Model):
    track = models.ForeignKey(ExamTrack, related_name='syllabus', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    topic = models.CharField(max_length=200)
    details = models.JSONField(default=list, help_text="List of bullet points")
    total_marks = models.PositiveIntegerField(default=100)
    highest_marks = models.PositiveIntegerField(default=0)
    highest_marks_info = models.CharField(max_length=200, blank=True, help_text="Details about the highest scorer, year etc.")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.track.slug} - {self.topic}"

class EligibilityCriteria(models.Model):
    track = models.OneToOneField(ExamTrack, related_name='eligibility', on_delete=models.CASCADE)
    age_limit = models.CharField(max_length=200)
    educational_qualification = models.TextField()
    nationality = models.CharField(max_length=200)
    other_details = models.JSONField(default=dict, help_text="Dictionary for extra notes like physical standards")
    category_eligibility = models.JSONField(default=dict, blank=True, help_text="Category-specific eligibility detail overrides")

    def __str__(self):
        return f"{self.track.slug} - Eligibility"

class DocumentVerification(models.Model):
    track = models.OneToOneField(ExamTrack, related_name='verification', on_delete=models.CASCADE)
    process_description = models.TextField()
    documents_required = models.JSONField(default=list, help_text="List of required documents")
    category_verification = models.JSONField(default=dict, blank=True, help_text="Category-specific verification document list overrides")

    def __str__(self):
        return f"{self.track.slug} - Verification"

class CutoffTrend(models.Model):
    track = models.ForeignKey(ExamTrack, related_name='cutoffs', on_delete=models.CASCADE)
    sub_exam_name = models.CharField(max_length=200, help_text="e.g., SSC CGL, SSC CHSL, CDS IMA")
    year = models.CharField(max_length=10)
    category = models.CharField(max_length=100, default='General (UR)')
    stages = models.JSONField(default=dict, help_text="JSON representation of stages and marks, e.g. {'Prelims': 88.22, 'Mains': 748}")

    class Meta:
        ordering = ['sub_exam_name', '-year']

    def __str__(self):
        return f"{self.sub_exam_name} ({self.year}) - {self.category}"

from django.contrib.auth.models import User
import django.utils.timezone

class Quiz(models.Model):
    date = models.DateField(default=django.utils.timezone.now)
    topic = models.CharField(max_length=200)
    track = models.ForeignKey(ExamTrack, related_name='quizzes', on_delete=models.CASCADE, null=True, blank=True)
    
    # Advanced metadata
    stage_name = models.CharField(max_length=200, default='Prelims')
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=600)
    total_marks = models.FloatField(default=100.0)
    marks_per_question = models.FloatField(default=2.0)
    negative_marking = models.FloatField(default=0.66)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('date', 'track', 'stage_name')
    
    def __str__(self):
        return f"Quiz - {self.date} - {self.track.slug if self.track else 'General'} - {self.stage_name}"

class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    text = models.TextField()
    options = models.JSONField(help_text="Dictionary of A, B, C, D options")
    correct_answer = models.CharField(max_length=5)
    explanation = models.TextField()
    subject = models.CharField(max_length=200, null=True, blank=True)
    difficulty = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order} for {self.quiz}"

class QuizRegistration(models.Model):
    user = models.ForeignKey(User, related_name='registrations', on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, related_name='registrations', on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'quiz')

    def __str__(self):
        return f"{self.user.username} - {self.quiz.date}"

class QuizSubmission(models.Model):
    user = models.ForeignKey(User, related_name='submissions', on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, related_name='submissions', on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    total_questions = models.IntegerField(default=0)
    time_taken_seconds = models.IntegerField(default=0)
    answers = models.JSONField(help_text="User's submitted answers")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'quiz')

    def __str__(self):
        return f"{self.user.username} - {self.quiz.date} - Score: {self.score}"
