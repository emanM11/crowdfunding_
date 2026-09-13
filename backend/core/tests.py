"""
Encoding of PROJECT_SPEC.md §3 / §5.7–5.9 / §6 as executable checks for the
core app: threaded comments (top-level list, replies only to top-level),
rating upsert with the 1–5 bound, reports targeting exactly one of
project/comment, homepage sections (top_rated only-running + only-rated,
latest, featured) and SQL stats, plus search with tag matching and dedupe.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from core.models import Comment, Rating, Report
from projects.models import Category, Donation, Project, Tag


def _make_user(email='u@example.com', password='Str0ng@Pass123', **extra):
    return User.objects.create_user(
        email=email,
        password=password,
        phone_number=extra.pop('phone_number', '01012345678'),
        first_name=extra.pop('first_name', 'سارة'),
        last_name=extra.pop('last_name', 'نبيل'),
        is_active=True,
        **extra,
    )


def _today():
    return timezone.localdate()


class CoreTestCase(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name='تقنية')
        self.owner = _make_user(email='owner@example.com')
        self.other = _make_user(email='other@example.com')
        self.client = APIClient()

    def create_project(self, creator=None, start=None, end=None, **extra):
        return Project.objects.create(
            title=extra.pop('title', 'مشروع المنصة'),
            details=extra.pop('details', 'تفاصيل'),
            category=self.category,
            creator=creator or self.owner,
            total_target=extra.pop('total_target', 1000),
            start_date=start or (_today() - timedelta(days=1)),
            end_date=end or (_today() + timedelta(days=30)),
            **extra,
        )


class CommentTests(CoreTestCase):

    def test_anon_cannot_post_comment(self):
        project = self.create_project()
        response = self.client.post(
            reverse('core:project-comments', args=[project.id]), {'text': 'مرحب'}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_posts_top_level_comment(self):
        project = self.create_project()
        self.client.force_authenticate(self.other)
        response = self.client.post(
            reverse('core:project-comments', args=[project.id]), {'text': 'مشروع رائع'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['first_name'], 'سارة')

    def test_comment_list_returns_only_top_level(self):
        project = self.create_project()
        top = Comment.objects.create(user=self.other, project=project, text='أعلى')
        Comment.objects.create(user=self.owner, project=project, text='رد', parent=top)
        response = self.client.get(reverse('core:project-comments', args=[project.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['text'], 'أعلى')
        self.assertEqual(len(results[0]['replies']), 1)

    def test_reply_to_top_level_comment(self):
        project = self.create_project()
        top = Comment.objects.create(user=self.other, project=project, text='أعلى')
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse('core:comment-reply', args=[top.id]), {'text': 'شكراً'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_reply_to_a_reply(self):
        project = self.create_project()
        top = Comment.objects.create(user=self.other, project=project, text='أعلى')
        reply = Comment.objects.create(user=self.owner, project=project, text='رد', parent=top)
        self.client.force_authenticate(self.other)
        response = self.client.post(
            reverse('core:comment-reply', args=[reply.id]), {'text': 'لا يمر'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RatingTests(CoreTestCase):

    def test_anon_cannot_rate(self):
        project = self.create_project()
        response = self.client.post(
            reverse('core:project-rate', args=[project.id]), {'value': 5}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rating_out_of_range_rejected(self):
        project = self.create_project()
        self.client.force_authenticate(self.other)
        for value in (0, 6):
            response = self.client.post(
                reverse('core:project-rate', args=[project.id]), {'value': value}
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=value)

    def test_rating_upserts_not_duplicates(self):
        project = self.create_project()
        self.client.force_authenticate(self.other)
        first = self.client.post(
            reverse('core:project-rate', args=[project.id]), {'value': 3}
        )
        self.assertEqual(first.data['rating_count'], 1)
        second = self.client.post(
            reverse('core:project-rate', args=[project.id]), {'value': 5}
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data['value'], 5)
        self.assertEqual(second.data['rating_count'], 1)
        self.assertEqual(Rating.objects.filter(project=project).count(), 1)

    def test_average_reflects_all_raters(self):
        project = self.create_project()
        self.client.force_authenticate(self.other)
        self.client.post(reverse('core:project-rate', args=[project.id]), {'value': 4})
        third = _make_user(email='third@example.com')
        self.client.force_authenticate(third)
        response = self.client.post(
            reverse('core:project-rate', args=[project.id]), {'value': 2}
        )
        self.assertEqual(response.data['average_rating'], 3)
        self.assertEqual(response.data['rating_count'], 2)


class ReportTests(CoreTestCase):

    def test_anon_cannot_report(self):
        project = self.create_project()
        response = self.client.post(
            reverse('core:report-create'), {'project': project.id, 'reason': 'إساءة'}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_report_project_only(self):
        project = self.create_project()
        self.client.force_authenticate(self.other)
        response = self.client.post(
            reverse('core:report-create'), {'project': project.id, 'reason': 'محتوى مخالف'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Report.objects.filter(reason='محتوى مخالف').count(), 1)

    def test_report_comment_only(self):
        project = self.create_project()
        comment = Comment.objects.create(user=self.owner, project=project, text='سيء')
        self.client.force_authenticate(self.other)
        response = self.client.post(
            reverse('core:report-create'), {'comment': comment.id, 'reason': 'إساءة'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_report_rejects_both_or_neither_target(self):
        project = self.create_project()
        comment = Comment.objects.create(user=self.owner, project=project, text='تعليق')
        self.client.force_authenticate(self.other)
        both = self.client.post(
            reverse('core:report-create'),
            {'project': project.id, 'comment': comment.id, 'reason': 'x'},
        )
        self.assertEqual(both.status_code, status.HTTP_400_BAD_REQUEST)
        neither = self.client.post(
            reverse('core:report-create'), {'reason': 'x'}
        )
        self.assertEqual(neither.status_code, status.HTTP_400_BAD_REQUEST)


class HomepageTests(CoreTestCase):

    def test_top_rated_only_includes_rated_running_projects(self):
        running = self.create_project(title='يعمل ومقيم')
        Rating.objects.create(user=self.other, project=running, value=5)
        ended = self.create_project(title='خلص وله تقييم', end=_today() - timedelta(days=1))
        Rating.objects.create(user=self.other, project=ended, value=5)
        unrated = self.create_project(title='يعمل بلا تقييم')

        response = self.client.get(reverse('core:homepage'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        top_titles = [p['title'] for p in response.data['top_rated']]
        self.assertIn('يعمل ومقيم', top_titles)
        self.assertNotIn('خلص وله تقييم', top_titles)
        self.assertNotIn('يعمل بلا تقييم', top_titles)

    def test_featured_only_returns_is_featured(self):
        featured = self.create_project(title='مميز', is_featured=True)
        self.create_project(title='غير مميز')
        response = self.client.get(reverse('core:homepage'))
        featured_titles = [p['title'] for p in response.data['featured']]
        self.assertIn('مميز', featured_titles)
        self.assertNotIn('غير مميز', featured_titles)

    def test_stats_are_aggregated_in_sql(self):
        project = self.create_project()
        Donation.objects.create(
            user=self.other, project=project, amount='40.00',
            status=Donation.STATUS_SUCCESSFUL,
        )
        Donation.objects.create(
            user=self.owner, project=project, amount='60.00',
            status=Donation.STATUS_SUCCESSFUL,
        )
        response = self.client.get(reverse('core:homepage'))
        self.assertEqual(response.data['stats']['projects'], 1)
        self.assertEqual(response.data['stats']['total_raised'], '100.00')
        self.assertEqual(response.data['stats']['backers'], 2)
        self.assertEqual(response.data['stats']['categories'], 1)

    def test_stats_ignore_pending_and_failed_donations(self):
        project = self.create_project()
        Donation.objects.create(user=self.other, project=project, amount='500.00')  # pending
        Donation.objects.create(
            user=self.other, project=project, amount='500.00',
            status=Donation.STATUS_FAILED,
        )
        response = self.client.get(reverse('core:homepage'))
        self.assertEqual(response.data['stats']['total_raised'], '0')
        self.assertEqual(response.data['stats']['backers'], 0)


class SearchTests(CoreTestCase):

    def test_empty_query_returns_no_projects(self):
        response = self.client.get(reverse('core:search'), {'q': ''})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], [])

    def test_matches_title_case_insensitively(self):
        self.create_project(title='تعليم القاهرة')
        other = self.create_project(title='شيء مختلف', creator=self.other)
        response = self.client.get(reverse('core:search'), {'q': 'تعليم'})
        titles = [p['title'] for p in response.data['results']]
        self.assertIn('تعليم القاهرة', titles)
        self.assertNotIn('شيء مختلف', titles)

    def test_matches_by_tag_name(self):
        tag = Tag.objects.create(name='بيئة')
        project = self.create_project(title='مبيدر نباتات')
        project.tags.add(tag)
        response = self.client.get(reverse('core:search'), {'q': 'بيئة'})
        titles = [p['title'] for p in response.data['results']]
        self.assertIn('مبيدر نباتات', titles)

    def test_no_duplicates_when_title_and_tag_both_match(self):
        tag = Tag.objects.create(name='مستشفى')
        project = self.create_project(title='بناء مستشفى')
        project.tags.add(tag)
        response = self.client.get(reverse('core:search'), {'q': 'مستشفى'})
        self.assertEqual(len(response.data['results']), 1)