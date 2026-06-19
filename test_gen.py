import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from exams.models import ExamTrack, Quiz
from datetime import date
from django.utils import timezone
from django.core.management import call_command

today = timezone.localtime().date()

# Delete existing 0-question quizzes for NDA and ESE
for track_slug in ['nda', 'ese']:
    Quiz.objects.filter(date=today, track__slug=track_slug).delete()

call_command('generate_daily_quiz')
