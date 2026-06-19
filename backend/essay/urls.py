from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EssaySessionViewSet,
    SubmitEssaySessionView,
    MobileUploadTokenView,
    MobileImageUploadView,
    ReviewerSubmissionsView,
    AnalyzeEssayQuestionView,
    EssayAnalysisDetailView,
    StaffEssayOverrideView,
    StaffEssaySessionDetailView
)

router = DefaultRouter()
router.register(r'sessions', EssaySessionViewSet, basename='essay-sessions')

urlpatterns = [
    path('', include(router.urls)),
    path('sessions/<int:pk>/submit/', SubmitEssaySessionView.as_view(), name='essay-session-submit'),
    path('upload/<str:token>/', MobileUploadTokenView.as_view(), name='essay-upload-info'),
    path('upload/<str:token>/submit/', MobileImageUploadView.as_view(), name='essay-upload-submit'),
    path('reviewer/submissions/', ReviewerSubmissionsView.as_view(), name='essay-reviewer-submissions'),
    path('questions/<int:pk>/analyze/', AnalyzeEssayQuestionView.as_view(), name='essay-question-analyze'),
    path('questions/<int:pk>/analysis/', EssayAnalysisDetailView.as_view(), name='essay-question-analysis'),
    path('reviewer/sessions/<int:pk>/', StaffEssaySessionDetailView.as_view(), name='staff-essay-session-detail'),
    path('reviewer/sessions/<int:pk>/override/', StaffEssayOverrideView.as_view(), name='staff-essay-session-override'),
]
