from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone
import datetime
from .models import ExamTrack, Quiz, QuizRegistration, QuizQuestion, QuizSubmission

class DailyQuizAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.user = User.objects.create_user(username='testuser', email='test@test.com', password='password123')
        
        # Create tracks
        self.track_upsc = ExamTrack.objects.create(
            slug='upsc', title='UPSC Civil Services', subtitle='GS', description='UPSC'
        )
        self.track_ssc = ExamTrack.objects.create(
            slug='ssc', title='Staff Selection Commission', subtitle='SSC CGL', description='SSC'
        )
        
        # Create quizzes for today
        self.today = timezone.now().date()
        self.quiz_upsc = Quiz.objects.create(
            date=self.today,
            topic='Economy and Environment',
            track=self.track_upsc,
            stage_name='Prelims',
            starts_at=timezone.now() + datetime.timedelta(hours=2),
            ends_at=timezone.now() + datetime.timedelta(hours=4),
            duration_seconds=600,
            total_marks=100.0,
            marks_per_question=2.0,
            negative_marking=0.66
        )
        self.quiz_ssc = Quiz.objects.create(
            date=self.today,
            topic='Arithmetic shortcuts',
            track=self.track_ssc,
            stage_name='Tier 1',
            starts_at=timezone.now() + datetime.timedelta(hours=3),
            ends_at=timezone.now() + datetime.timedelta(hours=5),
            duration_seconds=3600,
            total_marks=200.0,
            marks_per_question=2.0,
            negative_marking=0.5
        )

    def test_get_today_quizzes_all(self):
        url = reverse('quiz-today')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_today_quizzes_filtered_by_track(self):
        url = reverse('quiz-today')
        response = self.client.get(f"{url}?track=upsc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return a single dict, not a list
        self.assertIsInstance(response.data, dict)
        self.assertEqual(response.data['id'], self.quiz_upsc.id)
        self.assertEqual(response.data['track_slug'], 'upsc')
        self.assertEqual(response.data['status'], 'Not Registered')

    def test_get_today_quizzes_filtered_by_invalid_track_404(self):
        url = reverse('quiz-today')
        response = self.client.get(f"{url}?track=nonexistent")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_single_quiz_registration(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('quiz-register', kwargs={'pk': self.quiz_upsc.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify registration in DB
        self.assertTrue(QuizRegistration.objects.filter(user=self.user, quiz=self.quiz_upsc).exists())
        # Verify user is NOT registered for SSC quiz
        self.assertFalse(QuizRegistration.objects.filter(user=self.user, quiz=self.quiz_ssc).exists())

    def test_start_quiz_checks_registration_and_time(self):
        self.client.force_authenticate(user=self.user)
        
        # 1. Try to start when not registered -> Forbidden
        url = reverse('quiz-start', kwargs={'pk': self.quiz_upsc.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Register for the quiz
        QuizRegistration.objects.create(user=self.user, quiz=self.quiz_upsc)
        
        # 2. Try to start before starts_at -> Forbidden (starts_at is 2 hours in the future)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Shift quiz time to live (past start, future end)
        self.quiz_upsc.starts_at = timezone.now() - datetime.timedelta(hours=1)
        self.quiz_upsc.save()
        
        # 3. Try to start now -> OK
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class DailyLatestLeaderboardAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(username='rank1', email='r1@test.com', password='password123', first_name="Alice", last_name="One")
        self.user2 = User.objects.create_user(username='rank2', email='r2@test.com', password='password123', first_name="Bob", last_name="Two")
        self.user3 = User.objects.create_user(username='rank3', email='r3@test.com', password='password123', first_name="Charlie", last_name="Three")
        self.user4 = User.objects.create_user(username='rank4', email='r4@test.com', password='password123', first_name="David", last_name="Four")

        # Create track
        self.track = ExamTrack.objects.create(
            slug='upsc', title='UPSC Civil Services', subtitle='GS', description='UPSC'
        )

        # Create closed quiz
        self.today = timezone.now().date()
        self.quiz = Quiz.objects.create(
            date=self.today - datetime.timedelta(days=1),
            topic='Economy and Environment',
            track=self.track,
            stage_name='Prelims',
            starts_at=timezone.now() - datetime.timedelta(hours=5),
            ends_at=timezone.now() - datetime.timedelta(hours=2),
            duration_seconds=600,
            total_marks=100.0,
            marks_per_question=2.0,
            negative_marking=0.66
        )

        # Add 2 questions to the quiz
        self.q1 = QuizQuestion.objects.create(
            quiz=self.quiz, order=1, text="Q1", options={"A": "1", "B": "2"}, correct_answer="A", explanation=""
        )
        self.q2 = QuizQuestion.objects.create(
            quiz=self.quiz, order=2, text="Q2", options={"A": "1", "B": "2"}, correct_answer="B", explanation=""
        )

    def test_daily_latest_leaderboard_rankings_and_tie_breaks(self):
        now = timezone.now()
        
        # User 3 (Charlie): Score 2.0, accuracy 50%, time 200, submitted 3 min ago
        sub_charlie = QuizSubmission.objects.create(
            user=self.user3, quiz=self.quiz, score=2.0, total_questions=2, time_taken_seconds=200,
            answers={"1": "A", "2": "A"}  # 1 correct
        )
        sub_charlie.submitted_at = now - datetime.timedelta(minutes=3)
        sub_charlie.save()

        # User 2 (Bob): Score 2.0, accuracy 50%, time 150, submitted 2 mins ago (Better time than Charlie)
        sub_bob = QuizSubmission.objects.create(
            user=self.user2, quiz=self.quiz, score=2.0, total_questions=2, time_taken_seconds=150,
            answers={"1": "A", "2": "A"}  # 1 correct
        )
        sub_bob.submitted_at = now - datetime.timedelta(minutes=2)
        sub_bob.save()

        # User 4 (David): Score 2.0, accuracy 50%, time 150, submitted 1 min ago (Same score, accuracy, time as Bob, but Bob submitted earlier)
        sub_david = QuizSubmission.objects.create(
            user=self.user4, quiz=self.quiz, score=2.0, total_questions=2, time_taken_seconds=150,
            answers={"1": "A", "2": "A"}  # 1 correct
        )
        sub_david.submitted_at = now - datetime.timedelta(minutes=1)
        sub_david.save()

        # User 1 (Alice): Score 4.0, accuracy 100%, time 100, submitted 1 min ago (Best score)
        sub_alice = QuizSubmission.objects.create(
            user=self.user1, quiz=self.quiz, score=4.0, total_questions=2, time_taken_seconds=100,
            answers={"1": "A", "2": "B"}  # 2 correct
        )
        sub_alice.submitted_at = now - datetime.timedelta(minutes=1)
        sub_alice.save()

        url = reverse('leaderboard-daily-latest')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Retrieve the UPSC track data
        tracks = response.data['tracks']
        upsc_track = next(t for t in tracks if t['track_slug'] == 'upsc')
        
        self.assertEqual(upsc_track['quiz_id'], self.quiz.id)
        self.assertEqual(upsc_track['quiz_topic'], self.quiz.topic)
        
        rankers = upsc_track['rankers']
        # Should only return Top 3
        self.assertEqual(len(rankers), 3)

        self.assertEqual(rankers[0]['username'], 'rank1')  # Alice
        self.assertEqual(rankers[0]['rank'], 1)
        self.assertEqual(rankers[0]['accuracy'], 100.0)

        self.assertEqual(rankers[1]['username'], 'rank2')  # Bob
        self.assertEqual(rankers[1]['rank'], 2)
        self.assertEqual(rankers[1]['accuracy'], 50.0)

        self.assertEqual(rankers[2]['username'], 'rank4')  # David
        self.assertEqual(rankers[2]['rank'], 3)
        self.assertEqual(rankers[2]['accuracy'], 50.0)

    def test_daily_latest_leaderboard_empty_track(self):
        # Create a track with no quizzes
        empty_track = ExamTrack.objects.create(
            slug='empty', title='Empty Track', subtitle='Sub', description='Desc'
        )

        url = reverse('leaderboard-daily-latest')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        tracks = response.data['tracks']
        track_data = next(t for t in tracks if t['track_slug'] == 'empty')
        
        self.assertEqual(track_data['quiz_id'], None)
        self.assertEqual(track_data['rankers'], [])
