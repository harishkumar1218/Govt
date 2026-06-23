from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from threads.models import Thread, Answer

class ThreadsAPITests(APITestCase):
    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(username='aspirant1', email='aspirant1@example.com', password='password123')
        self.user2 = User.objects.create_user(username='aspirant2', email='aspirant2@example.com', password='password123')
        
        # Set urls
        self.list_create_url = reverse('thread-list-create')
        
        # Authenticate as user1 by default
        self.client.force_authenticate(user=self.user1)

    def test_create_thread(self):
        data = {
            'title': 'How to prep for Polity?', 
            'body': 'Polity seems very vast, any tips?',
            'tags': ['Polity', 'GS2']
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], data['title'])
        self.assertEqual(response.data['authorId'], self.user1.id)
        self.assertEqual(response.data['upvoteCount'], 0)
        self.assertEqual(response.data['answerCount'], 0)
        self.assertEqual(response.data['tags'], ['Polity', 'GS2'])
        self.assertEqual(response.data['isSolved'], False)
        self.assertEqual(response.data['viewCount'], 0)

    def test_list_threads(self):
        # Create threads
        Thread.objects.create(title='Polity Prep', body='Tips please', author=self.user1)
        Thread.objects.create(title='History Prep', body='Ancient history help', author=self.user2)

        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['totalCount'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_search_threads(self):
        Thread.objects.create(title='Polity Notes', body='Here are some notes', author=self.user1)
        Thread.objects.create(title='Economics Guidance', body='Fiscal policy rules', author=self.user2)

        # Search for polity
        response = self.client.get(self.list_create_url, {'q': 'polity'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['totalCount'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Polity Notes')

    def test_sort_threads(self):
        t1 = Thread.objects.create(title='Polity Notes', body='Polity is simple', author=self.user1)
        t2 = Thread.objects.create(title='Economics Guidance', body='Fiscal policy', author=self.user2)

        # Upvote t2
        t2.upvotes.add(self.user1)
        t2.upvotes.add(self.user2)

        # Sort by upvotes
        response = self.client.get(self.list_create_url, {'sort': 'upvotes'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['id'], t2.id)

    def test_thread_detail_view_count(self):
        thread = Thread.objects.create(title='Syllabus doubt', body='What is CSAT?', author=self.user2)
        url = reverse('thread-detail', kwargs={'pk': thread.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Syllabus doubt')
        self.assertEqual(response.data['viewCount'], 1)
        self.assertIn('answers', response.data)
        
        # Second view
        response2 = self.client.get(url)
        self.assertEqual(response2.data['viewCount'], 2)

    def test_edit_thread_permission(self):
        thread = Thread.objects.create(title='Syllabus doubt', body='What is CSAT?', author=self.user2)
        url = reverse('thread-detail', kwargs={'pk': thread.id})

        # Try to edit other's thread
        data = {'title': 'Updated Title'}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Edit own thread
        self.client.force_authenticate(user=self.user2)
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')

    def test_delete_thread_permission(self):
        thread = Thread.objects.create(title='Doubt', body='Why is GS so hard?', author=self.user2)
        url = reverse('thread-detail', kwargs={'pk': thread.id})

        # Try to delete other's thread
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Delete own thread
        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Thread.objects.filter(id=thread.id).exists())

    def test_upvote_thread(self):
        thread = Thread.objects.create(title='Great post', body='Interesting facts', author=self.user2)
        url = reverse('thread-upvote', kwargs={'pk': thread.id})

        # Upvote
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['upvoteCount'], 1)
        self.assertTrue(response.data['hasCurrentUserUpvoted'])

        # Remove upvote
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['upvoteCount'], 0)
        self.assertFalse(response.data['hasCurrentUserUpvoted'])

    def test_answer_flow(self):
        thread = Thread.objects.create(title='Doubt', body='Explain CR?', author=self.user2)
        create_ans_url = reverse('answer-create', kwargs={'thread_pk': thread.id})

        # Create answer
        response = self.client.post(create_ans_url, {'body': 'Cognitive reflection is...'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['body'], 'Cognitive reflection is...')
        self.assertEqual(response.data['authorId'], self.user1.id)
        self.assertEqual(response.data['isAccepted'], False)
        
        answer_id = response.data['id']
        ans_detail_url = reverse('answer-detail', kwargs={'pk': answer_id})

        # Edit answer
        response = self.client.put(ans_detail_url, {'body': 'Updated cognitive reflection answer'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['body'], 'Updated cognitive reflection answer')

        # Try to delete other's answer
        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(ans_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Delete own answer
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(ans_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Answer.objects.filter(id=answer_id).exists())

    def test_create_thread_invalid_category(self):
        data = {'title': 'Invalid Category', 'body': 'This should fail', 'category': 'Physics'}
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', response.data)

    def test_create_thread_valid_category(self):
        data = {'title': 'Polity Doubt', 'body': 'Explain Article 21', 'category': 'Polity'}
        response = self.client.post(self.list_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['category'], 'Polity')

    def test_filter_by_category(self):
        Thread.objects.create(title='Polity Notes', body='Polity is simple', author=self.user1, category='Polity')
        Thread.objects.create(title='Economics Guidance', body='Fiscal policy', author=self.user2, category='Economy')

        response = self.client.get(self.list_create_url, {'category': 'Polity'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['totalCount'], 1)
        self.assertEqual(response.data['results'][0]['category'], 'Polity')

    def test_stats_endpoint(self):
        t1 = Thread.objects.create(title='Polity Notes', body='Polity is simple', author=self.user1, category='Polity')
        t2 = Thread.objects.create(title='Economics Guidance', body='Fiscal policy', author=self.user2, category='Economy')
        Answer.objects.create(thread=t1, body='This is polity answer', author=self.user2)

        stats_url = reverse('thread-stats')
        response = self.client.get(stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['totalThreads'], 2)
        self.assertEqual(response.data['totalAnswers'], 1)
        self.assertEqual(response.data['categoryCounts']['Polity'], 1)
        self.assertEqual(response.data['categoryCounts']['Economy'], 1)
        self.assertEqual(response.data['categoryCounts']['History'], 0)

    def test_accept_answer_flow(self):
        # Create thread owned by user1
        thread = Thread.objects.create(title='Doubt about GS4', body='Any essay advice?', author=self.user1)
        answer = Answer.objects.create(thread=thread, body='Write structured arguments.', author=self.user2)

        accept_url = reverse('thread-accept-answer', kwargs={'pk': thread.id, 'answer_pk': answer.id})

        # Try to accept answer as user2 (not owner)
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(accept_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Accept answer as user1 (owner)
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(accept_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['isSolved'], True)
        self.assertEqual(response.data['acceptedAnswerId'], answer.id)

        # Verify thread detail reflects accepted answer
        detail_url = reverse('thread-detail', kwargs={'pk': thread.id})
        detail_resp = self.client.get(detail_url)
        self.assertEqual(detail_resp.data['isSolved'], True)
        self.assertEqual(detail_resp.data['acceptedAnswerId'], answer.id)
        self.assertEqual(detail_resp.data['answers'][0]['id'], answer.id)
        self.assertEqual(detail_resp.data['answers'][0]['isAccepted'], True)

        # Unaccept answer
        response = self.client.delete(accept_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['isSolved'], False)
        self.assertEqual(response.data['acceptedAnswerId'], None)

        detail_resp = self.client.get(detail_url)
        self.assertEqual(detail_resp.data['isSolved'], False)
        self.assertEqual(detail_resp.data['acceptedAnswerId'], None)
        self.assertEqual(detail_resp.data['answers'][0]['isAccepted'], False)
