from rest_framework import serializers
from .models import ExamTrack, ExamStage, SyllabusSection, EligibilityCriteria, DocumentVerification, CutoffTrend

class ExamStageSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='stage_type') # Map back to frontend expectation

    class Meta:
        model = ExamStage
        fields = ['title', 'type', 'duration', 'description']

class SyllabusSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyllabusSection
        fields = ['topic', 'details', 'total_marks', 'highest_marks', 'highest_marks_info']

class EligibilityCriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EligibilityCriteria
        fields = ['age_limit', 'educational_qualification', 'nationality', 'other_details', 'category_eligibility']

class DocumentVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVerification
        fields = ['process_description', 'documents_required', 'category_verification']

class CutoffTrendSerializer(serializers.ModelSerializer):
    class Meta:
        model = CutoffTrend
        fields = ['sub_exam_name', 'year', 'category', 'stages']

class ExamTrackSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='slug') # Map back to frontend expectation
    flowchart = ExamStageSerializer(many=True, read_only=True)
    syllabus = SyllabusSectionSerializer(many=True, read_only=True)
    eligibility = EligibilityCriteriaSerializer(read_only=True)
    verification = DocumentVerificationSerializer(read_only=True)
    cutoffs = CutoffTrendSerializer(many=True, read_only=True)

    class Meta:
        model = ExamTrack
        fields = ['id', 'title', 'subtitle', 'description', 'gradient', 'flowchart', 'syllabus', 'eligibility', 'verification', 'cutoffs']
