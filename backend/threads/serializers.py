from django.db.models import Count
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Thread, Answer

class TagListField(serializers.Field):
    def to_representation(self, value):
        if not value:
            return []
        return [t.strip() for t in value.split(',') if t.strip()]

    def to_internal_value(self, data):
        if isinstance(data, list):
            return ",".join([str(t).strip() for t in data if str(t).strip()])
        if isinstance(data, str):
            return data
        return ""

class AnswerSerializer(serializers.ModelSerializer):
    authorId = serializers.IntegerField(source='author.id', read_only=True)
    authorName = serializers.CharField(source='author.username', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    upvoteCount = serializers.SerializerMethodField(method_name='get_upvote_count')
    hasCurrentUserUpvoted = serializers.SerializerMethodField(method_name='get_has_current_user_upvoted')
    threadId = serializers.IntegerField(source='thread.id', read_only=True)
    isAccepted = serializers.SerializerMethodField(method_name='get_is_accepted')

    class Meta:
        model = Answer
        fields = [
            'id', 'threadId', 'body', 'authorId', 'authorName', 
            'createdAt', 'updatedAt', 'upvoteCount', 'hasCurrentUserUpvoted', 'isAccepted'
        ]
        read_only_fields = ['id', 'threadId', 'authorId', 'authorName', 'createdAt', 'updatedAt']

    def get_upvote_count(self, obj):
        return obj.upvotes.count()

    def get_has_current_user_upvoted(self, obj):
        user = self.context.get('request').user if 'request' in self.context else None
        if user and user.is_authenticated:
            return obj.upvotes.filter(id=user.id).exists()
        return False

    def get_is_accepted(self, obj):
        return obj.thread.accepted_answer_id == obj.id

class ThreadSerializer(serializers.ModelSerializer):
    authorId = serializers.IntegerField(source='author.id', read_only=True)
    authorName = serializers.CharField(source='author.username', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    upvoteCount = serializers.SerializerMethodField(method_name='get_upvote_count')
    answerCount = serializers.SerializerMethodField(method_name='get_answer_count')
    hasCurrentUserUpvoted = serializers.SerializerMethodField(method_name='get_has_current_user_upvoted')
    shareUrl = serializers.SerializerMethodField(method_name='get_share_url')
    
    # Extended fields for industry-ready Q&A features
    isSolved = serializers.BooleanField(source='is_solved', required=False)
    acceptedAnswerId = serializers.PrimaryKeyRelatedField(source='accepted_answer', read_only=True)
    tags = TagListField(required=False, default="")
    viewCount = serializers.IntegerField(source='view_count', read_only=True)

    class Meta:
        model = Thread
        fields = [
            'id', 'title', 'body', 'category', 'authorId', 'authorName', 
            'createdAt', 'updatedAt', 'upvoteCount', 'answerCount',
            'hasCurrentUserUpvoted', 'shareUrl', 'isSolved', 'acceptedAnswerId', 'tags', 'viewCount'
        ]
        read_only_fields = ['id', 'authorId', 'authorName', 'createdAt', 'updatedAt', 'viewCount', 'acceptedAnswerId']

    def validate_category(self, value):
        allowed = ['Polity', 'Economy', 'History', 'Geography', 'Current Affairs', 'Essay', 'CSAT', 'Ethics', 'Optional', 'General']
        if value not in allowed:
            raise serializers.ValidationError(f"Category must be one of: {', '.join(allowed)}")
        return value

    def get_upvote_count(self, obj):
        return obj.upvotes.count()

    def get_answer_count(self, obj):
        return obj.answers.count()

    def get_has_current_user_upvoted(self, obj):
        user = self.context.get('request').user if 'request' in self.context else None
        if user and user.is_authenticated:
            return obj.upvotes.filter(id=user.id).exists()
        return False

    def get_share_url(self, obj):
        return f"?tab=threads&threadId={obj.id}"

class ThreadDetailSerializer(ThreadSerializer):
    answers = serializers.SerializerMethodField(method_name='get_sorted_answers')

    class Meta(ThreadSerializer.Meta):
        fields = ThreadSerializer.Meta.fields + ['answers']

    def get_sorted_answers(self, obj):
        accepted_id = obj.accepted_answer_id
        if accepted_id:
            queryset = obj.answers.annotate(upvote_num=Count('upvotes')).order_by('-upvote_num', '-created_at')
            serialized = AnswerSerializer(queryset, many=True, context=self.context).data
            # Move the accepted answer to index 0 (pinned)
            accepted_idx = next((i for i, a in enumerate(serialized) if a['id'] == accepted_id), -1)
            if accepted_idx > -1:
                accepted_answer = serialized.pop(accepted_idx)
                serialized.insert(0, accepted_answer)
            return serialized
        else:
            queryset = obj.answers.annotate(upvote_num=Count('upvotes')).order_by('-upvote_num', '-created_at')
            return AnswerSerializer(queryset, many=True, context=self.context).data
