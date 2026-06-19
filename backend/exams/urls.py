from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExamTrackViewSet, GenerateMockExamView, CurrentAffairsView, DailyQuizView, RegisterQuizView, QuizStartView, QuizSubmitView, LeaderboardView, DailyLatestLeaderboardView, UserAnalyticsView, UserMockHistoryListView, UserMockHistoryDetailView, PlatformConfigView

router = DefaultRouter()
router.register(r'tracks', ExamTrackViewSet, basename='track')

urlpatterns = [
    path('config/', PlatformConfigView.as_view(), name='platform-config'),
    path('generate-mock/', GenerateMockExamView.as_view(), name='generate-mock'),
    path('current-affairs/', CurrentAffairsView.as_view(), name='current-affairs'),
    path('quiz/today/', DailyQuizView.as_view(), name='quiz-today'),
    path('quiz/<int:pk>/register/', RegisterQuizView.as_view(), name='quiz-register'),
    path('quiz/<int:pk>/start/', QuizStartView.as_view(), name='quiz-start'),
    path('quiz/<int:pk>/submit/', QuizSubmitView.as_view(), name='quiz-submit'),
    path('leaderboard/daily-latest/', DailyLatestLeaderboardView.as_view(), name='leaderboard-daily-latest'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('user/analytics/', UserAnalyticsView.as_view(), name='user-analytics'),
    path('user/mock-history/', UserMockHistoryListView.as_view(), name='user-mock-history'),
    path('user/mock-history/<int:pk>/', UserMockHistoryDetailView.as_view(), name='user-mock-history-detail'),
    path('', include(router.urls)),
]
