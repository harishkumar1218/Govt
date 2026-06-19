from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from exams.models import ExamTrack
from roadmap.models import UserRoadmapProgress
from roadmap.serializers import RoadmapProgressUpdateSerializer
from roadmap.services import get_roadmap_for_track, get_seed_templates, get_roadmap_collection

class RoadmapView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, track_slug):
        # Validate track exists in SQLite
        if not ExamTrack.objects.filter(slug=track_slug).exists():
            return Response({"detail": f"Track '{track_slug}' not found."}, status=status.HTTP_404_NOT_FOUND)

        roadmap_data = get_roadmap_for_track(request.user, track_slug)
        if not roadmap_data:
            return Response({"detail": "Roadmap not found for this track."}, status=status.HTTP_404_NOT_FOUND)

        return Response(roadmap_data)

class RoadmapCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, track_slug, item_id):
        # Validate track exists in SQLite
        if not ExamTrack.objects.filter(slug=track_slug).exists():
            return Response({"detail": f"Track '{track_slug}' not found."}, status=status.HTTP_404_NOT_FOUND)

        # Validate item exists in templates
        templates = []
        try:
            col = get_roadmap_collection()
            templates = list(col.find({"track_slug": track_slug, "id": item_id}))
        except Exception:
            pass

        # Fallback check
        if not templates:
            templates = [t for t in get_seed_templates() if t['track_slug'] == track_slug and t['id'] == item_id]

        if not templates:
            return Response({"detail": f"Roadmap item '{item_id}' not found in track '{track_slug}'."}, status=status.HTTP_404_NOT_FOUND)

        # Update or create progress as completed
        progress, created = UserRoadmapProgress.objects.get_or_create(
            user=request.user,
            track_slug=track_slug,
            roadmap_item_id=item_id,
            defaults={'status': 'completed', 'completed_at': timezone.now()}
        )
        if not created and progress.status != 'completed':
            progress.status = 'completed'
            progress.completed_at = timezone.now()
            progress.save()

        # Retrieve the updated full roadmap to provide updated progress summary and recommended next item
        updated_roadmap = get_roadmap_for_track(request.user, track_slug)

        return Response({
            "detail": f"Item {item_id} marked as completed.",
            "updated_item": {
                "id": item_id,
                "status": "completed",
                "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
            },
            "overall_completion": updated_roadmap['overall_completion'],
            "completed_count": updated_roadmap['completed_count'],
            "total_count": updated_roadmap['total_count'],
            "recommended_next_item_id": updated_roadmap['recommended_next_item_id'],
            "priority_reason": updated_roadmap['priority_reason'],
            "roadmap": updated_roadmap
        })

class RoadmapStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, track_slug, item_id):
        # Validate track exists in SQLite
        if not ExamTrack.objects.filter(slug=track_slug).exists():
            return Response({"detail": f"Track '{track_slug}' not found."}, status=status.HTTP_404_NOT_FOUND)

        # Validate item exists
        templates = []
        try:
            col = get_roadmap_collection()
            templates = list(col.find({"track_slug": track_slug, "id": item_id}))
        except Exception:
            pass

        if not templates:
            templates = [t for t in get_seed_templates() if t['track_slug'] == track_slug and t['id'] == item_id]

        if not templates:
            return Response({"detail": f"Roadmap item '{item_id}' not found in track '{track_slug}'."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RoadmapProgressUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data['status']
        completed_at = timezone.now() if new_status == 'completed' else None

        progress, created = UserRoadmapProgress.objects.get_or_create(
            user=request.user,
            track_slug=track_slug,
            roadmap_item_id=item_id,
            defaults={'status': new_status, 'completed_at': completed_at}
        )
        if not created:
            progress.status = new_status
            progress.completed_at = completed_at
            progress.save()

        updated_roadmap = get_roadmap_for_track(request.user, track_slug)

        return Response({
            "detail": f"Item {item_id} status updated to {new_status}.",
            "updated_item": {
                "id": item_id,
                "status": new_status,
                "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
            },
            "overall_completion": updated_roadmap['overall_completion'],
            "completed_count": updated_roadmap['completed_count'],
            "total_count": updated_roadmap['total_count'],
            "recommended_next_item_id": updated_roadmap['recommended_next_item_id'],
            "priority_reason": updated_roadmap['priority_reason'],
            "roadmap": updated_roadmap
        })
