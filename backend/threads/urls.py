from django.urls import path
from .views import (
    ThreadListCreateView, ThreadDetailView, ThreadUpvoteView,
    AnswerCreateView, AnswerDetailView, AnswerUpvoteView, ThreadStatsView,
    ThreadAcceptAnswerView
)

urlpatterns = [
    path('', ThreadListCreateView.as_view(), name='thread-list-create'),
    path('stats/', ThreadStatsView.as_view(), name='thread-stats'),
    path('<int:pk>/', ThreadDetailView.as_view(), name='thread-detail'),
    path('<int:pk>/upvote/', ThreadUpvoteView.as_view(), name='thread-upvote'),
    path('<int:thread_pk>/answers/', AnswerCreateView.as_view(), name='answer-create'),
    path('<int:pk>/answers/<int:answer_pk>/accept/', ThreadAcceptAnswerView.as_view(), name='thread-accept-answer'),
    path('answers/<int:pk>/', AnswerDetailView.as_view(), name='answer-detail'),
    path('answers/<int:pk>/upvote/', AnswerUpvoteView.as_view(), name='answer-upvote'),
]
