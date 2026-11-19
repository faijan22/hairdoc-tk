from datetime import timedelta
from importlib import import_module
from uuid import uuid4

from django.apps import apps as django_apps
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.consultations.models import Appointment, ConsultationCase, ConsultationService
from apps.messaging.models import Conversation, ConversationMember, Message
from apps.messaging.services import ensure_consultation_conversation
from apps.notifications.models import Notification


class ConversationIdentityTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            "repeat-client@example.com", "HairDoc!2026Strong", is_email_verified=True,
        )
        self.tk = User.objects.create_user(
            "repeat-tk@example.com", "HairDoc!2026Strong", is_email_verified=True, is_staff=True,
        )
        self.service = ConsultationService.objects.create(
            name="Repeat consultation",
            slug=f"repeat-{uuid4()}",
            short_description="Talk to TK.",
            description="Talk to TK.",
            duration_minutes=30,
            price_amount="60",
            currency="GBP",
            status=ConsultationService.Status.PUBLISHED,
            published_at=timezone.now(),
            expert=self.tk,
        )

    def _confirmed_appointment(self, days_ahead):
        case = ConsultationCase.objects.create(
            client=self.client_user,
            service=self.service,
            status=ConsultationCase.Status.PHOTOS_COMPLETE,
            timezone_snapshot="Europe/London",
            service_name=self.service.name,
            duration_minutes=30,
            price_amount="60",
            currency="GBP",
            intake_completed_at=timezone.now(),
            photos_completed_at=timezone.now(),
        )
        starts_at = timezone.now() + timedelta(days=days_ahead)
        return Appointment.objects.create(
            case=case,
            client=self.client_user,
            expert=self.tk,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=30),
            status=Appointment.Status.CONFIRMED,
            client_timezone="Europe/London",
            expert_timezone="Europe/London",
        )

    def test_later_consultation_reuses_the_existing_direct_conversation(self):
        original = ensure_consultation_conversation(self._confirmed_appointment(2))
        reused = ensure_consultation_conversation(self._confirmed_appointment(7))

        self.assertEqual(reused.pk, original.pk)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_migration_merges_existing_duplicates_into_the_message_bearing_thread(self):
        original = ensure_consultation_conversation(self._confirmed_appointment(2))
        original_message = Message.objects.create(
            conversation=original,
            sender=self.client_user,
            client_message_id=uuid4(),
            body="Earlier history",
        )
        later_appointment = self._confirmed_appointment(7)
        duplicate = Conversation.objects.create(consultation=later_appointment.case)
        duplicate_client = ConversationMember.objects.create(
            conversation=duplicate,
            user=self.client_user,
            role=ConversationMember.Role.CLIENT,
        )
        ConversationMember.objects.create(
            conversation=duplicate,
            user=self.tk,
            role=ConversationMember.Role.EXPERT,
        )
        duplicate_message = Message.objects.create(
            conversation=duplicate,
            sender=self.tk,
            client_message_id=uuid4(),
            body="Newer duplicate-thread message",
        )
        duplicate_client.last_read_message = duplicate_message
        duplicate_client.save(update_fields=("last_read_message", "updated_at"))
        notice = Notification.objects.create(
            recipient=self.client_user,
            kind=Notification.Kind.NEW_MESSAGE,
            title="New private message",
            body="You have a new message from TK.",
            route=f"/messages/{duplicate.public_id}",
            conversation=duplicate,
            message=duplicate_message,
        )

        migration = import_module(
            "apps.messaging.migrations.0006_merge_duplicate_direct_conversations"
        )
        migration.merge_duplicate_direct_conversations(django_apps, None)

        self.assertEqual(Conversation.objects.count(), 1)
        self.assertTrue(Conversation.objects.filter(pk=original.pk).exists())
        self.assertEqual(
            set(Message.objects.values_list("pk", flat=True)),
            {original_message.pk, duplicate_message.pk},
        )
        self.assertFalse(Conversation.objects.filter(pk=duplicate.pk).exists())
        notice.refresh_from_db()
        self.assertEqual(notice.conversation_id, original.pk)
        self.assertEqual(notice.route, f"/messages/{original.public_id}")
        canonical_client = ConversationMember.objects.get(
            conversation=original,
            user=self.client_user,
        )
        self.assertEqual(canonical_client.last_read_message_id, duplicate_message.pk)
