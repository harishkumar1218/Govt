import os
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from exams.models import ExamTrack, ExamStage, SyllabusSection, EligibilityCriteria, DocumentVerification, CutoffTrend
from pymongo import MongoClient

class Command(BaseCommand):
    help = 'Exports all SQLite exam data to MongoDB Atlas and creates a structured local JSON file backup in /DB/'

    def handle(self, *args, **options):
        self.stdout.write("Reading data from SQLite...")

        client = None
        collection = None
        mongo_uri = settings.MONGO_DB_URI
        if not mongo_uri:
            self.stderr.write('[Warning] MONGO_DB not configured. Local backups will still be exported.')
        else:
            try:
                client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
                client.admin.command('ping')
                db = client['govt-cluster']
                collection = db['exams']
                self.stdout.write("Connected to MongoDB Atlas successfully.")
            except Exception as e:
                self.stderr.write(f"[Warning] Failed to connect to MongoDB Atlas: {e}. Local backups will still be exported.")

        tracks = ExamTrack.objects.all()

        db_dir = Path(settings.BASE_DIR).parent / 'DB' / 'exams'
        db_dir.mkdir(parents=True, exist_ok=True)
        
        for track in tracks:
            # Build nested MongoDB document
            doc = {
                "_id": track.slug,
                "slug": track.slug,
                "title": track.title,
                "subtitle": track.subtitle,
                "description": track.description,
                "gradient": track.gradient,
                
                "flowchart": [
                    {
                        "title": stage.title,
                        "type": stage.stage_type,
                        "duration": stage.duration,
                        "description": stage.description
                    }
                    for stage in track.flowchart.all()
                ],
                
                "syllabus": [
                    {
                        "topic": section.topic,
                        "total_marks": section.total_marks,
                        "highest_marks": section.highest_marks,
                        "highest_marks_info": section.highest_marks_info,
                        "details": section.details
                    }
                    for section in track.syllabus.all()
                ]
            }
            
            # Eligibility
            try:
                el = track.eligibility
                doc["eligibility"] = {
                    "age_limit": el.age_limit,
                    "educational_qualification": el.educational_qualification,
                    "nationality": el.nationality,
                    "other_details": el.other_details,
                    "category_eligibility": el.category_eligibility
                }
            except EligibilityCriteria.DoesNotExist:
                doc["eligibility"] = {}

            # Verification
            try:
                ver = track.verification
                doc["verification"] = {
                    "process_description": ver.process_description,
                    "documents_required": ver.documents_required,
                    "category_verification": ver.category_verification
                }
            except DocumentVerification.DoesNotExist:
                doc["verification"] = {}
                
            # Cutoffs
            doc["cutoffs"] = [
                {
                    "sub_exam_name": cutoff.sub_exam_name,
                    "year": cutoff.year,
                    "category": cutoff.category,
                    "stages": cutoff.stages
                }
                for cutoff in track.cutoffs.all()
            ]
            
            # 1. Save locally in structured folder
            file_path = db_dir / f"{track.slug}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(doc, f, indent=2, ensure_ascii=False)
            self.stdout.write(f"Saved local backup: DB/exams/{track.slug}.json")
            
            # 2. Push to MongoDB Atlas
            if collection is not None:
                try:
                    collection.replace_one({"_id": track.slug}, doc, upsert=True)
                    self.stdout.write(self.style.SUCCESS(f"Successfully uploaded {track.slug} to MongoDB Atlas."))
                except Exception as e:
                    self.stderr.write(f"Failed to upload {track.slug} to MongoDB: {e}")

        self.stdout.write(self.style.SUCCESS("All tasks completed!"))
