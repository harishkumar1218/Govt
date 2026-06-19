import json
from django.core.management.base import BaseCommand

from core.config_loader import load_exam_data_from_json, load_slug_registry, get_pattern_path
from exams.models import (
    ExamTrack, ExamStage, SyllabusSection, EligibilityCriteria,
    DocumentVerification, CutoffTrend, ExamPattern,
)


def seed_exam_patterns():
    registry = load_slug_registry()
    for track_slug, mapping in registry.get('tracks', {}).items():
        try:
            track = ExamTrack.objects.get(slug=track_slug)
        except ExamTrack.DoesNotExist:
            continue

        pattern_path = get_pattern_path(track_slug)
        if not pattern_path or not pattern_path.exists():
            continue

        with open(pattern_path, encoding='utf-8') as f:
            pattern_data = json.load(f)

        default_stage = mapping.get('default_stage', 'Prelims')
        stage = next(
            (s for s in pattern_data.get('stages', []) if s['stage_name'] == default_stage),
            pattern_data['stages'][0] if pattern_data.get('stages') else None,
        )
        if not stage:
            continue

        paper = None
        for p in stage.get('papers', []):
            if not p.get('qualifying', False) and p.get('number_of_questions'):
                paper = p
                break
        if not paper and stage.get('papers'):
            paper = stage['papers'][0]
        if not paper:
            continue

        last_verified = pattern_data.get('last_verified')
        ExamPattern.objects.update_or_create(
            track=track,
            stage_name=stage['stage_name'],
            defaults={
                'total_questions': paper.get('number_of_questions', 10),
                'duration_seconds': paper.get('duration_minutes', 10) * 60,
                'marks_per_question': paper.get('marks_per_question', 2.0),
                'negative_marking': paper.get('negative_marking', 0.5),
                'source_url': pattern_data.get('official_source_url', ''),
            },
        )


class Command(BaseCommand):
    help = 'Seeds exam tracks from DB/exams/*.json and exam patterns from *-pattern.json'

    def handle(self, *args, **kwargs):
        exam_data = load_exam_data_from_json()
        if not exam_data:
            self.stderr.write('No exam JSON files found in DB/exams/')
            return

        self.stdout.write('Seeding database from JSON config...')
        for slug, data in exam_data.items():
            track, _ = ExamTrack.objects.update_or_create(
                slug=slug,
                defaults={
                    'title': data['title'],
                    'subtitle': data['subtitle'],
                    'description': data['description'],
                    'gradient': data['gradient'],
                },
            )

            track.flowchart.all().delete()
            track.syllabus.all().delete()
            EligibilityCriteria.objects.filter(track=track).delete()
            DocumentVerification.objects.filter(track=track).delete()
            CutoffTrend.objects.filter(track=track).delete()

            for idx, stage in enumerate(data.get('flowchart', [])):
                ExamStage.objects.create(
                    track=track,
                    order=idx,
                    title=stage['title'],
                    stage_type=stage['type'],
                    duration=stage['duration'],
                    description=stage['description'],
                )

            for idx, section in enumerate(data.get('syllabus', [])):
                SyllabusSection.objects.create(
                    track=track,
                    order=idx,
                    topic=section['topic'],
                    details=section['details'],
                    total_marks=section.get('total_marks', 100),
                    highest_marks=section.get('highest_marks', 0),
                    highest_marks_info=section.get('highest_marks_info', ''),
                )

            if 'eligibility' in data:
                EligibilityCriteria.objects.create(
                    track=track,
                    age_limit=data['eligibility']['age_limit'],
                    educational_qualification=data['eligibility']['educational_qualification'],
                    nationality=data['eligibility']['nationality'],
                    other_details=data['eligibility']['other_details'],
                    category_eligibility=data['eligibility'].get('category_eligibility', {}),
                )

            if 'verification' in data:
                DocumentVerification.objects.create(
                    track=track,
                    process_description=data['verification']['process_description'],
                    documents_required=data['verification']['documents_required'],
                    category_verification=data['verification'].get('category_verification', {}),
                )

            for cutoff in data.get('cutoffs', []):
                CutoffTrend.objects.create(
                    track=track,
                    sub_exam_name=cutoff['sub_exam_name'],
                    year=cutoff['year'],
                    category=cutoff.get('category', 'General (UR)'),
                    stages=cutoff['stages'],
                )

            self.stdout.write(self.style.SUCCESS(f'Successfully seeded {slug}'))

        seed_exam_patterns()
        self.stdout.write(self.style.SUCCESS('Exam patterns seeded from *-pattern.json files'))

        self.stdout.write('Syncing database to MongoDB Atlas...')
        from django.core.management import call_command
        call_command('push_to_mongodb')
