from rest_framework import serializers
from .models import EssayPracticeSession, EssayQuestion, EssayAnswerImage, EssayReview, EssayAnswerTranscript, EssayAIReview

class EssayAnswerImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EssayAnswerImage
        fields = ['id', 'image', 'page_number', 'uploaded_at', 'original_filename', 'file_size']
        read_only_fields = ['id', 'uploaded_at', 'image'] # The actual file upload will be handled specially

class EssayAIReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = EssayAIReview
        fields = ['id', 'status', 'total_score', 'max_score', 'percentage', 'rating_band', 'review_json', 'strengths', 'weaknesses', 'suggestions', 'created_at', 'updated_at']

class EssayAnswerTranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = EssayAnswerTranscript
        fields = ['id', 'combined_text', 'word_count', 'extraction_quality']

class EssayQuestionSerializer(serializers.ModelSerializer):
    images = EssayAnswerImageSerializer(many=True, read_only=True)
    ai_review = EssayAIReviewSerializer(read_only=True)
    transcript = EssayAnswerTranscriptSerializer(read_only=True)

    class Meta:
        model = EssayQuestion
        fields = ['id', 'prompt_text', 'order', 'max_marks', 'upload_token', 'images', 'ai_review', 'transcript']
        read_only_fields = ['id', 'upload_token']

class EssayReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)

    class Meta:
        model = EssayReview
        fields = ['id', 'reviewer_name', 'marks_awarded', 'feedback', 'rubric', 'reviewed_at']
        read_only_fields = ['id', 'reviewer_name', 'reviewed_at']

class EssayPracticeSessionSerializer(serializers.ModelSerializer):
    questions = EssayQuestionSerializer(many=True, read_only=True)
    review = EssayReviewSerializer(read_only=True)

    class Meta:
        model = EssayPracticeSession
        fields = ['id', 'track_slug', 'roadmap_item_id', 'title', 'status', 'created_at', 'submitted_at', 'questions', 'review']
        read_only_fields = ['id', 'created_at', 'submitted_at', 'status', 'user']
