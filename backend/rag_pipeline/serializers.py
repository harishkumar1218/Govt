from rest_framework import serializers

class GenerateMockTestSerializer(serializers.Serializer):
    exam = serializers.CharField(max_length=100)
    topic = serializers.CharField(max_length=255)
    num_questions = serializers.IntegerField(default=10, min_value=1, max_value=50)

class ResearchUpdateSerializer(serializers.Serializer):
    urls = serializers.ListField(child=serializers.URLField())
    exam = serializers.CharField(max_length=100)
    subject = serializers.CharField(max_length=100)
    topic = serializers.CharField(max_length=255)
