from django.db import models
from django.contrib.auth.models import User

class UserRoadmapProgress(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roadmap_progress')
    track_slug = models.CharField(max_length=100)
    roadmap_item_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'track_slug', 'roadmap_item_id')
        indexes = [
            models.Index(fields=['user', 'track_slug', 'roadmap_item_id']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.track_slug} - {self.roadmap_item_id} - {self.status}"
