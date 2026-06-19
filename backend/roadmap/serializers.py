from rest_framework import serializers
from roadmap.models import UserRoadmapProgress

class RoadmapProgressUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRoadmapProgress
        fields = ['status']
        extra_kwargs = {
            'status': {'required': True}
        }
