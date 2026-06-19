from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from exams.models import ExamTrack
from roadmap.models import UserRoadmapProgress

class RoadmapAPITests(APITestCase):

    def setUp(self):
        # Create test users
        self.user_a = User.objects.create_user(username='user_a', email='a@test.com', password='password123')
        self.user_b = User.objects.create_user(username='user_b', email='b@test.com', password='password123')
        
        # Create mock track in SQLite (as required by view validation)
        self.track = ExamTrack.objects.create(
            slug='upsc',
            title='UPSC Civil Services',
            subtitle='Civil Services Examination',
            description='Test track',
            gradient='linear-gradient(to right, #000, #fff)'
        )

    def test_anonymous_user_cannot_access_roadmap(self):
        url = reverse('roadmap-detail', kwargs={'track_slug': 'upsc'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_fetch_roadmap_defaults_to_not_started(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse('roadmap-detail', kwargs={'track_slug': 'upsc'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['track_slug'], 'upsc')
        self.assertEqual(data['overall_completion'], 0)
        self.assertEqual(data['completed_count'], 0)
        
        # Check first item status is not_started
        first_node = data['phases'][0]['nodes'][0]
        self.assertEqual(first_node['status'], 'not_started')

    def test_completing_item_persists_in_db(self):
        self.client.force_authenticate(user=self.user_a)
        
        # Complete item u-1
        url = reverse('roadmap-complete', kwargs={'track_slug': 'upsc', 'item_id': 'u-1'})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_item']['status'], 'completed')
        
        # Verify in DB
        progress = UserRoadmapProgress.objects.get(user=self.user_a, track_slug='upsc', roadmap_item_id='u-1')
        self.assertEqual(progress.status, 'completed')
        self.assertIsNotNone(progress.completed_at)
        
        # Fetch roadmap again to check merged state
        detail_url = reverse('roadmap-detail', kwargs={'track_slug': 'upsc'})
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.data['completed_count'], 1)
        self.assertGreater(detail_response.data['overall_completion'], 0)

    def test_user_isolation(self):
        # User A completes u-1
        self.client.force_authenticate(user=self.user_a)
        url = reverse('roadmap-complete', kwargs={'track_slug': 'upsc', 'item_id': 'u-1'})
        self.client.post(url)
        
        # Log in as User B
        self.client.force_authenticate(user=self.user_b)
        detail_url = reverse('roadmap-detail', kwargs={'track_slug': 'upsc'})
        response = self.client.get(detail_url)
        
        # User B should show 0 completed items
        self.assertEqual(response.data['completed_count'], 0)
        self.assertEqual(response.data['overall_completion'], 0)
        
        first_node = response.data['phases'][0]['nodes'][0]
        self.assertEqual(first_node['status'], 'not_started')

    def test_invalid_track_returns_404(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse('roadmap-detail', kwargs={'track_slug': 'invalid-track'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_item_returns_404(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse('roadmap-complete', kwargs={'track_slug': 'upsc', 'item_id': 'invalid-item'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_recommendation_falls_back_safely_when_no_quiz_history_exists(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse('roadmap-detail', kwargs={'track_slug': 'upsc'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should recommend first item u-1 by default
        self.assertEqual(response.data['recommended_next_item_id'], 'u-1')
        self.assertEqual(response.data['priority_reason'], 'Recommended next step in your study plan.')
