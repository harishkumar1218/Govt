from django.db import models
from django.contrib.auth.models import User

class Thread(models.Model):
    title = models.CharField(max_length=120)
    body = models.TextField()
    category = models.CharField(max_length=50, default='General')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='threads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    upvotes = models.ManyToManyField(User, related_name='upvoted_threads', blank=True)
    
    # Extended fields for industry-ready system
    is_solved = models.BooleanField(default=False)
    accepted_answer = models.ForeignKey('Answer', on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_for_thread')
    tags = models.CharField(max_length=255, default='', blank=True)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Answer(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='answers')
    body = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    upvotes = models.ManyToManyField(User, related_name='upvoted_answers', blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Answer by {self.author.username} to {self.thread.title}"
