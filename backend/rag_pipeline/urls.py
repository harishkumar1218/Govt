from django.urls import path
from .views import GenerateMockTestView, ResearchUpdateView

urlpatterns = [
    path('generate-mock-test/', GenerateMockTestView.as_view(), name='generate-mock-test'),
    path('research/update/', ResearchUpdateView.as_view(), name='research-update'),
]
