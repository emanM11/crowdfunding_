from django.conf import settings
from django.db import models

from projects.models import Project


class Comment(models.Model):
    """PROJECT_SPEC.md 5.7. `parent` enables threaded replies (bonus)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='comments')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.user} on {self.project}'


class Rating(models.Model):
    """
    PROJECT_SPEC.md 5.8. unique_together enforces one rating per user per
    project at the DB level; the view additionally upserts (updates the
    existing row) rather than relying on this to raise an error.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ratings')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='ratings')
    value = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ('user', 'project')

    def __str__(self):
        return f'{self.value} by {self.user} on {self.project}'


class Report(models.Model):
    """
    PROJECT_SPEC.md 5.9. Exactly one of `project` / `comment` must be set —
    enforced in the serializer, not here, so a clear 400 with a field-level
    message is returned instead of an IntegrityError/CheckConstraint failure.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reports')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.project or self.comment
        return f'Report by {self.user} on {target}'
