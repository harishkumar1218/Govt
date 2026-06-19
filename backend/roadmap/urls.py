from django.urls import path
from roadmap.views import RoadmapView, RoadmapCompleteView, RoadmapStatusView

urlpatterns = [
    path('<slug:track_slug>/', RoadmapView.as_view(), name='roadmap-detail'),
    path('<slug:track_slug>/<str:item_id>/complete/', RoadmapCompleteView.as_view(), name='roadmap-complete'),
    path('<slug:track_slug>/<str:item_id>/status/', RoadmapStatusView.as_view(), name='roadmap-status'),
]
