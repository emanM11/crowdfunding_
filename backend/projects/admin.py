from django.contrib import admin

from .models import (
    Category,
    Donation,
    Project,
    ProjectImage,
    ProjectUpdate,
    RewardTier,
    Tag,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


class ProjectUpdateInline(admin.TabularInline):
    model = ProjectUpdate
    extra = 0


class RewardTierInline(admin.TabularInline):
    model = RewardTier
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    # Admins: view all projects, toggle is_featured, view status (PROJECT_SPEC.md 13)
    list_display = ['title', 'category', 'creator', 'total_target', 'display_status', 'is_featured', 'created_at']
    list_filter = ['status', 'is_featured', 'category']
    list_editable = ['is_featured']
    search_fields = ['title', 'creator__email']
    inlines = [ProjectImageInline, ProjectUpdateInline, RewardTierInline]
    autocomplete_fields = ['creator', 'category']
    filter_horizontal = ['tags']

    @admin.display(description='status')
    def display_status(self, obj):
        # `status` the raw DB field only ever stores 'running' or
        # 'cancelled' directly — 'ended' is derived from today's date vs
        # end_date and would otherwise never show up in this list at all.
        return obj.computed_status


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['project__title', 'user__email']
