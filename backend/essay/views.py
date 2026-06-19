import random
import uuid

from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, views, status, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from core.config_loader import load_platform_config, get_essay_prompts_for_track
from .models import EssayPracticeSession, EssayQuestion, EssayAnswerImage, EssayReview
from .serializers import EssayPracticeSessionSerializer, EssayQuestionSerializer


def _essay_max_marks(_track_slug: str) -> int:
    return load_platform_config()['essay']['default_max_marks']


class EssaySessionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EssayPracticeSessionSerializer

    def get_queryset(self):
        return EssayPracticeSession.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        track_slug = request.data.get('track_slug')
        roadmap_item_id = request.data.get('roadmap_item_id')
        essay_cfg = load_platform_config()['essay']
        title = request.data.get('title', essay_cfg['default_title'])

        if not track_slug or not roadmap_item_id:
            return Response(
                {"error": "track_slug and roadmap_item_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = EssayPracticeSession.objects.create(
            user=request.user,
            track_slug=track_slug,
            roadmap_item_id=roadmap_item_id,
            title=title,
            status='in_progress',
        )

        prompts = get_essay_prompts_for_track(track_slug)
        if len(prompts) < essay_cfg['questions_per_session']:
            return Response(
                {"error": f"Not enough essay prompts configured for track '{track_slug}'."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        selected_prompts = random.sample(prompts, essay_cfg['questions_per_session'])
        max_marks = _essay_max_marks(track_slug)

        for idx, prompt_text in enumerate(selected_prompts):
            EssayQuestion.objects.create(
                session=session,
                prompt_text=prompt_text,
                order=idx + 1,
                max_marks=max_marks,
            )

        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SubmitEssaySessionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(EssayPracticeSession, pk=pk, user=request.user)
        if session.status != 'in_progress':
            return Response(
                {"error": f"Cannot submit session with status {session.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.status = 'submitted'
        session.submitted_at = timezone.now()
        session.save()
        return Response({"message": "Session submitted successfully"}, status=status.HTTP_200_OK)


class MobileUploadTokenView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            uuid_token = uuid.UUID(token)
            question = EssayQuestion.objects.get(upload_token=uuid_token)
        except (ValueError, EssayQuestion.DoesNotExist):
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "question_id": question.id,
            "prompt_text": question.prompt_text,
            "session_title": question.session.title,
            "order": question.order,
            "max_marks": question.max_marks,
        })


class MobileImageUploadView(views.APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, token):
        try:
            uuid_token = uuid.UUID(token)
            question = EssayQuestion.objects.get(upload_token=uuid_token)
        except (ValueError, EssayQuestion.DoesNotExist):
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_404_NOT_FOUND)

        if question.session.status != 'in_progress':
            return Response(
                {"error": "This session has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        files = request.FILES.getlist('images')
        if not files:
            return Response({"error": "No images provided"}, status=status.HTTP_400_BAD_REQUEST)

        current_pages = question.images.count()
        uploaded_images = []

        for idx, file in enumerate(files):
            if file.size > 10 * 1024 * 1024:
                return Response(
                    {"error": f"File {file.name} exceeds 10MB limit"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            img = EssayAnswerImage.objects.create(
                question=question,
                user=question.session.user,
                image=file,
                page_number=current_pages + idx + 1,
                original_filename=file.name,
                file_size=file.size,
                content_type=file.content_type,
            )
            uploaded_images.append(img)

        return Response({
            "message": f"Successfully uploaded {len(uploaded_images)} pages.",
            "uploaded_count": len(uploaded_images),
        }, status=status.HTTP_201_CREATED)


class ReviewerSubmissionsView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        sessions = EssayPracticeSession.objects.filter(
            status__in=['submitted', 'reviewed']
        ).order_by('-submitted_at')
        serializer = EssayPracticeSessionSerializer(sessions, many=True)
        return Response(serializer.data)


class AnalyzeEssayQuestionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        question = get_object_or_404(EssayQuestion, pk=pk, session__user=request.user)

        from .services.ocr_service import extract_text_from_question_images
        transcript = extract_text_from_question_images(question.id)
        if not transcript:
            return Response(
                {"error": "Failed to extract text or no images found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .services.evaluation_service import evaluate_essay
        review = evaluate_essay(transcript.id)
        if not review:
            return Response({"error": "Evaluation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from .serializers import EssayQuestionSerializer
        serializer = EssayQuestionSerializer(question)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EssayAnalysisDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        question = get_object_or_404(EssayQuestion, pk=pk, session__user=request.user)
        from .serializers import EssayQuestionSerializer
        serializer = EssayQuestionSerializer(question)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StaffEssayOverrideView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        session = get_object_or_404(EssayPracticeSession, pk=pk)

        marks_awarded = request.data.get('marks_awarded', 0)
        feedback = request.data.get('feedback', '')

        session.status = 'reviewed'
        session.save()

        review, _ = EssayReview.objects.update_or_create(
            session=session,
            defaults={
                'reviewer': request.user,
                'marks_awarded': float(marks_awarded),
                'feedback': feedback,
                'rubric': request.data.get('rubric', {}),
            },
        )

        from .serializers import EssayReviewSerializer
        return Response(EssayReviewSerializer(review).data, status=status.HTTP_200_OK)


class StaffEssaySessionDetailView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        session = get_object_or_404(EssayPracticeSession, pk=pk)
        from .serializers import EssayPracticeSessionSerializer
        return Response(EssayPracticeSessionSerializer(session).data, status=status.HTTP_200_OK)
