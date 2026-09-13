from rest_framework import serializers

from .models import Comment, Rating, Report


class CommentAuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class ReplySerializer(serializers.ModelSerializer):
    """One level of nested replies — PROJECT_SPEC.md 5.7 bonus. Replies to
    replies aren't supported (parent must be a top-level comment; enforced
    in CommentCreateSerializer), so this never needs to recurse further."""
    user = CommentAuthorSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'text', 'parent', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    user = CommentAuthorSerializer(read_only=True)
    replies = ReplySerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'text', 'parent', 'created_at', 'replies']


class CommentCreateSerializer(serializers.ModelSerializer):
    """POST /api/projects/<id>/comments/ always creates a top-level
    comment. Replies go through the dedicated
    POST /api/comments/<id>/reply/ endpoint instead (see
    ReplyCreateSerializer below) — keeping the two endpoints' jobs
    separate avoids ambiguity about where `parent` is allowed to come from.
    """
    class Meta:
        model = Comment
        fields = ['id', 'text']

    def create(self, validated_data):
        return Comment.objects.create(
            user=self.context['request'].user,
            project=self.context['project'],
            parent=None,
            **validated_data,
        )


class ReplyCreateSerializer(serializers.ModelSerializer):
    """POST /api/comments/<id>/reply/ — the parent is taken from the URL,
    not the request body."""
    class Meta:
        model = Comment
        fields = ['id', 'text']

    def create(self, validated_data):
        parent = self.context['parent']
        return Comment.objects.create(
            user=self.context['request'].user,
            project=parent.project,
            parent=parent,
            **validated_data,
        )


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['value']

    def validate_value(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError('value must be between 1 and 5.')
        return value


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'project', 'comment', 'reason', 'created_at']

    def validate(self, attrs):
        project = attrs.get('project')
        comment = attrs.get('comment')
        if bool(project) == bool(comment):
            # Both set, or neither set — exactly one is required.
            raise serializers.ValidationError(
                'Provide exactly one of `project` or `comment` to report.'
            )
        return attrs

    def create(self, validated_data):
        return Report.objects.create(user=self.context['request'].user, **validated_data)
