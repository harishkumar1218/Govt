from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, F
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Thread, Answer
from .serializers import ThreadSerializer, ThreadDetailSerializer, AnswerSerializer

class ThreadListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Thread.objects.all()

        # Category filter
        category = request.query_params.get('category', None)
        if category and category.lower() != 'all':
            queryset = queryset.filter(category__iexact=category)

        # Search filter
        search_query = request.query_params.get('q', None)
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(body__icontains=search_query)
            )

        # Sorting option
        sort = request.query_params.get('sort', 'new').lower()
        if sort in ('upvotes', 'top'):
            queryset = queryset.annotate(upvote_num=Count('upvotes')).order_by('-upvote_num', '-created_at')
        elif sort in ('answers', 'answered', 'most_answered'):
            queryset = queryset.annotate(answer_num=Count('answers')).order_by('-answer_num', '-created_at')
        elif sort == 'unanswered':
            queryset = queryset.annotate(answer_num=Count('answers')).filter(answer_num=0).order_by('-created_at')
        elif sort == 'solved':
            queryset = queryset.filter(is_solved=True).order_by('-created_at')
        else:
            queryset = queryset.order_by('-created_at')

        # Pagination
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('pageSize', 10))
        except ValueError:
            page = 1
            page_size = 10

        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = queryset.count()
        paginated_queryset = queryset[start:end]

        serializer = ThreadSerializer(paginated_queryset, many=True, context={'request': request})
        
        return Response({
            "results": serializer.data,
            "totalCount": total_count,
            "page": page,
            "pageSize": page_size,
            "hasMore": end < total_count
        })

    def post(self, request):
        serializer = ThreadSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ThreadDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        thread = get_object_or_404(Thread, pk=pk)
        
        # Safe atomic view count increment
        Thread.objects.filter(pk=pk).update(view_count=F('view_count') + 1)
        thread.refresh_from_db()
        
        serializer = ThreadDetailSerializer(thread, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        thread = get_object_or_404(Thread, pk=pk)
        if thread.author != request.user:
            return Response({"detail": "You do not have permission to edit this thread."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ThreadSerializer(thread, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        thread = get_object_or_404(Thread, pk=pk)
        if thread.author != request.user:
            return Response({"detail": "You do not have permission to delete this thread."}, status=status.HTTP_403_FORBIDDEN)
        
        thread.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ThreadUpvoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        thread = get_object_or_404(Thread, pk=pk)
        thread.upvotes.add(request.user)
        return Response({
            "detail": "Upvoted successfully", 
            "upvoteCount": thread.upvotes.count(), 
            "hasCurrentUserUpvoted": True
        })

    def delete(self, request, pk):
        thread = get_object_or_404(Thread, pk=pk)
        thread.upvotes.remove(request.user)
        return Response({
            "detail": "Upvote removed", 
            "upvoteCount": thread.upvotes.count(), 
            "hasCurrentUserUpvoted": False
        })

class AnswerCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_pk):
        thread = get_object_or_404(Thread, pk=thread_pk)
        serializer = AnswerSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(author=request.user, thread=thread)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AnswerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        answer = get_object_or_404(Answer, pk=pk)
        if answer.author != request.user:
            return Response({"detail": "You do not have permission to edit this answer."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = AnswerSerializer(answer, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        answer = get_object_or_404(Answer, pk=pk)
        if answer.author != request.user:
            return Response({"detail": "You do not have permission to delete this answer."}, status=status.HTTP_403_FORBIDDEN)
        
        # If it was the accepted answer, clear it on the thread
        if hasattr(answer.thread, 'accepted_answer') and answer.thread.accepted_answer == answer:
            answer.thread.accepted_answer = None
            answer.thread.is_solved = False
            answer.thread.save()
            
        answer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AnswerUpvoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        answer = get_object_or_404(Answer, pk=pk)
        answer.upvotes.add(request.user)
        return Response({
            "detail": "Upvoted successfully", 
            "upvoteCount": answer.upvotes.count(), 
            "hasCurrentUserUpvoted": True
        })

    def delete(self, request, pk):
        answer = get_object_or_404(Answer, pk=pk)
        answer.upvotes.remove(request.user)
        return Response({
            "detail": "Upvote removed", 
            "upvoteCount": answer.upvotes.count(), 
            "hasCurrentUserUpvoted": False
        })

class ThreadAcceptAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, answer_pk):
        thread = get_object_or_404(Thread, pk=pk)
        if thread.author != request.user:
            return Response({"detail": "Only the doubt author can accept an answer."}, status=status.HTTP_403_FORBIDDEN)

        answer = get_object_or_404(Answer, pk=answer_pk, thread=thread)
        thread.accepted_answer = answer
        thread.is_solved = True
        thread.save()

        return Response({
            "detail": "Answer accepted successfully.",
            "isSolved": True,
            "acceptedAnswerId": answer.id
        })

    def delete(self, request, pk, answer_pk):
        thread = get_object_or_404(Thread, pk=pk)
        if thread.author != request.user:
            return Response({"detail": "Only the doubt author can modify this thread."}, status=status.HTTP_403_FORBIDDEN)

        if thread.accepted_answer_id == answer_pk:
            thread.accepted_answer = None
            thread.is_solved = False
            thread.save()

        return Response({
            "detail": "Answer unaccepted successfully.",
            "isSolved": False,
            "acceptedAnswerId": None
        })

class ThreadStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_threads = Thread.objects.count()
        total_answers = Answer.objects.count()
        
        categories = ['Polity', 'Economy', 'History', 'Geography', 'Current Affairs', 'Essay', 'CSAT', 'Ethics', 'Optional', 'General']
        category_counts = {}
        for cat in categories:
            category_counts[cat] = Thread.objects.filter(category=cat).count()
            
        return Response({
            "totalThreads": total_threads,
            "totalAnswers": total_answers,
            "categoryCounts": category_counts
        })
