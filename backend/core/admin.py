from django.contrib import admin

from .models import Comment, Rating, Report


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'text', 'parent', 'created_at']
    list_filter = ['created_at']
    search_fields = ['text', 'user__email', 'project__title']


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'value']
    list_filter = ['value']
    search_fields = ['project__title', 'user__email']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    # Admins: review reports (PROJECT_SPEC.md 13)
    list_display = ['id', 'user', 'project', 'comment', 'reason', 'created_at']
    list_filter = ['created_at']
    search_fields = ['reason', 'user__email']
