from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import GenerateMockTestSerializer, ResearchUpdateSerializer
from knowledge.tasks import research_internet
# Note: generate_mock_test would be imported from rag_pipeline.tasks

class GenerateMockTestView(APIView):
    def post(self, request):
        serializer = GenerateMockTestSerializer(data=request.data)
        if serializer.is_valid():
            # In full implementation, we'd trigger a Celery task here
            # task = generate_mock_test_task.delay(
            #     serializer.validated_data['exam'],
            #     serializer.validated_data['topic'],
            #     serializer.validated_data['num_questions']
            # )
            return Response({"status": "processing", "message": "Mock test generation started"}, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResearchUpdateView(APIView):
    def post(self, request):
        serializer = ResearchUpdateSerializer(data=request.data)
        if serializer.is_valid():
            urls = serializer.validated_data['urls']
            exam = serializer.validated_data['exam']
            subject = serializer.validated_data['subject']
            topic = serializer.validated_data['topic']
            
            task_ids = []
            for url in urls:
                task = research_internet.delay(url, exam, subject, topic)
                task_ids.append(task.id)
                
            return Response({"status": "processing", "tasks": task_ids}, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
