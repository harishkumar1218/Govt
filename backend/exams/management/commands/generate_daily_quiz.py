import os
import subprocess
from datetime import datetime, timedelta, time as dt_time

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from core.config_loader import load_platform_config, get_quiz_schedule_for_weekday, get_track_mapping
from exams.models import Quiz, QuizQuestion, ExamTrack, ExamPattern


class Command(BaseCommand):
    help = 'Generates daily quizzes for all tracks using config-driven schedule and RAG engine'

    def handle(self, *args, **kwargs):
        platform = load_platform_config()
        quiz_cfg = platform['quiz']
        llm_cfg = platform['llm']

        self.stdout.write('Initializing Multi-Track Daily Quiz Generation...')
        today = timezone.now().date()
        base_topic = get_quiz_schedule_for_weekday(today.weekday())

        tracks = ExamTrack.objects.all()
        if not tracks.exists():
            self.stdout.write('No ExamTracks found. Skipping generation.')
            return

        rag_dir = os.path.abspath(os.path.join(settings.BASE_DIR.parent, 'RAG'))
        python_exec = os.path.join(rag_dir, 'venv', 'bin', 'python')
        script_path = os.path.join(rag_dir, 'generate_exam.py')
        output_file = os.path.join(settings.BASE_DIR, 'temp_daily_quiz.md')

        start_dt = timezone.make_aware(
            datetime.combine(
                today,
                dt_time(quiz_cfg['default_start_hour'], quiz_cfg['default_start_minute']),
            )
        )

        for track in tracks:
            topic = f"{track.title} - {base_topic}"
            mapping = get_track_mapping(track.slug) or {}
            pattern = ExamPattern.objects.filter(track=track).first()

            duration = pattern.duration_seconds if pattern else quiz_cfg['default_duration_seconds']
            num_questions = str(
                quiz_cfg['default_questions_per_quiz']
                if not pattern
                else min(quiz_cfg['default_questions_per_quiz'], pattern.total_questions)
            )
            marks_per_q = pattern.marks_per_question if pattern else 2.0
            negative = pattern.negative_marking if pattern else 0.66
            stage_name = pattern.stage_name if pattern else mapping.get('default_stage', 'Prelims')
            total_marks = float(num_questions) * marks_per_q

            self.stdout.write(f'\nProcessing Track: {track.title} | Topic: {topic}')

            quiz, created = Quiz.objects.get_or_create(
                date=today,
                track=track,
                stage_name=stage_name,
                defaults={
                    'topic': topic,
                    'starts_at': start_dt,
                    'ends_at': start_dt + timedelta(seconds=duration),
                    'duration_seconds': duration,
                    'total_marks': total_marks,
                    'marks_per_question': marks_per_q,
                    'negative_marking': negative,
                },
            )
            if not created:
                self.stdout.write(f'Quiz for {track.title} on {today} already exists. Regenerating...')
                QuizQuestion.objects.filter(quiz=quiz).delete()
                quiz.topic = topic
                quiz.starts_at = start_dt
                quiz.ends_at = start_dt + timedelta(seconds=duration)
                quiz.duration_seconds = duration
                quiz.total_marks = total_marks
                quiz.marks_per_question = marks_per_q
                quiz.negative_marking = negative
                quiz.save()

            try:
                self.stdout.write(f'RAG Engine generating questions via subprocess for {track.title}...')
                cmd = [
                    python_exec, script_path,
                    '--topic', topic,
                    '--num_questions', num_questions,
                    '--model', llm_cfg['default_model'],
                    '--output', output_file,
                ]
                subprocess.run(cmd, cwd=rag_dir, check=True, text=True)

                with open(output_file, encoding='utf-8') as f:
                    raw_markdown = f.read()

                if os.path.exists(output_file):
                    os.remove(output_file)

                from exams.views import GenerateMockExamView
                parser = GenerateMockExamView()
                questions = parser.parse_markdown_to_json(raw_markdown)

                if not questions:
                    self.stderr.write(f'Failed to parse questions for {track.title}. Raw output was:\n{raw_markdown}\n')
                    continue

                for idx, q in enumerate(questions, start=1):
                    options_dict = {}
                    for opt_idx, opt in enumerate(q['options']):
                        letter = chr(65 + opt_idx)
                        options_dict[letter] = opt

                    QuizQuestion.objects.create(
                        quiz=quiz,
                        order=idx,
                        text=q['text'],
                        options=options_dict,
                        correct_answer=chr(65 + q['correctAnswer']),
                        explanation=q['explanation'],
                    )

                self.stdout.write(self.style.SUCCESS(
                    f'Successfully generated {len(questions)} questions for {track.title}.'
                ))

            except subprocess.CalledProcessError as e:
                self.stderr.write(f'Error generating quiz subprocess for {track.title}: {e}')
            except Exception as e:
                self.stderr.write(f'Error parsing quiz for {track.title}: {e}')
