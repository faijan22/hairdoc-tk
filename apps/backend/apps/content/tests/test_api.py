from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.content.models import ContentItem


class PublicContentApiTests(TestCase):
    def setUp(self):
        self.published = ContentItem.objects.create(
            type=ContentItem.Type.TEDX,
            title="Published talk",
            slug="published-talk",
            summary="Visible public summary.",
            status=ContentItem.Status.PUBLISHED,
            display_order=2,
            published_at=timezone.now(),
        )
        ContentItem.objects.create(
            type=ContentItem.Type.BOOK,
            title="Draft book",
            slug="draft-book",
            summary="Not visible yet.",
            status=ContentItem.Status.DRAFT,
            display_order=1,
        )
        ContentItem.objects.create(
            type=ContentItem.Type.RESOURCE,
            title="Scheduled resource",
            slug="scheduled-resource",
            summary="Not visible before its publication date.",
            status=ContentItem.Status.PUBLISHED,
            published_at=timezone.now() + timedelta(days=1),
        )

    def test_list_returns_only_currently_published_content(self):
        response = self.client.get(reverse("content:list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["public_id"], str(self.published.public_id))

    def test_detail_hides_drafts(self):
        draft = ContentItem.objects.get(slug="draft-book")

        response = self.client.get(reverse("content:detail", kwargs={"public_id": draft.public_id}))

        self.assertEqual(response.status_code, 404)

