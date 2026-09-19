from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import NotificationPreference, User
from apps.accounts.services import create_device_session
from apps.consultations.models import Appointment, ConsultationCase, ConsultationService
from apps.messaging.services import create_message, ensure_consultation_conversation
from apps.notifications.models import EmailDelivery, Notification, PushDelivery, PushDevice
from apps.notifications.services import notify_appointment_confirmed
from apps.notifications.tasks import (
    create_due_appointment_reminders,
    deliver_notification,
    reconcile_push_receipts,
)


@override_settings(PUSH_NOTIFICATIONS_ENABLED=False)
class MessageNotificationTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user("notify-client@example.com", "HairDoc!2026Strong", is_email_verified=True)
        self.tk = User.objects.create_user("notify-tk@example.com", "HairDoc!2026Strong", is_email_verified=True, is_staff=True)
        service = ConsultationService.objects.create(
            name="Notification consultation", slug=f"notify-{uuid4()}", short_description="Talk to TK.",
            description="Talk to TK.", duration_minutes=30, price_amount="60", currency="GBP",
            status=ConsultationService.Status.PUBLISHED, published_at=timezone.now(), expert=self.tk,
        )
        self.case = ConsultationCase.objects.create(
            client=self.client_user, service=service, status=ConsultationCase.Status.PHOTOS_COMPLETE,
            timezone_snapshot="Europe/London", service_name=service.name, duration_minutes=30,
            price_amount="60", currency="GBP", intake_completed_at=timezone.now(), photos_completed_at=timezone.now(),
        )
        self.appointment = Appointment.objects.create(
            case=self.case, client=self.client_user, expert=self.tk, starts_at=timezone.now() + timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=1, minutes=30), status=Appointment.Status.CONFIRMED,
            client_timezone="Europe/London", expert_timezone="Europe/London",
        )
        self.conversation = ensure_consultation_conversation(self.appointment)
        access, _, _ = create_device_session(self.client_user, "Notification test")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_device_is_user_scoped_and_message_creates_private_notification(self):
        device = self.client.post(reverse("notifications:push-device-list-create"), {
            "expo_token": "ExponentPushToken[test-token]", "platform": "IOS", "device_id": "phone-1",
        }, format="json")
        self.assertEqual(device.status_code, 201)
        self.assertNotIn("Hello", device.json().get("expo_token", ""))

        with self.captureOnCommitCallbacks(execute=True):
            message, _ = create_message(self.conversation, self.tk, "Sensitive message text", uuid4())
        notification = Notification.objects.get(message=message)
        self.assertEqual(notification.recipient, self.client_user)
        self.assertNotIn("Sensitive", notification.body)
        self.assertEqual(PushDelivery.objects.filter(notification=notification).count(), 1)
        listing = self.client.get(reverse("notifications:notification-list"))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["unread_count"], 1)
        self.assertEqual(listing.json()["results"][0]["conversation_public_id"], str(self.conversation.public_id))
        self.assertEqual(listing.json()["results"][0]["route"], f"/messages/{self.conversation.public_id}")

    def test_message_preference_suppresses_notification(self):
        NotificationPreference.objects.update_or_create(
            user=self.client_user, defaults={"message_notifications": False},
        )
        with self.captureOnCommitCallbacks(execute=True):
            create_message(self.conversation, self.tk, "No alert", uuid4())
        self.assertFalse(Notification.objects.exists())

    def test_notification_center_is_scoped_and_can_mark_all_read(self):
        notify_appointment_confirmed(self.appointment)
        client_notification = Notification.objects.get(
            recipient=self.client_user, kind=Notification.Kind.APPOINTMENT_CONFIRMED,
        )
        Notification.objects.create(
            recipient=self.tk, kind=Notification.Kind.CONSULTATION_SUBMITTED,
            title="Private staff update", body="For TK only.", route="/staff/appointments",
            dedupe_key="staff-only",
        )

        listing = self.client.get(reverse("notifications:notification-list"))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["unread_count"], 1)
        self.assertEqual(len(listing.json()["results"]), 1)
        self.assertEqual(listing.json()["results"][0]["public_id"], str(client_notification.public_id))

        response = self.client.post(reverse("notifications:notification-read-all"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"unread_count": 0})
        client_notification.refresh_from_db()
        self.assertIsNotNone(client_notification.read_at)
        self.assertIsNone(Notification.objects.get(dedupe_key="staff-only").read_at)

    def test_appointment_events_and_reminders_are_idempotent(self):
        NotificationPreference.objects.update_or_create(
            user=self.client_user, defaults={"timezone": "Asia/Kolkata"},
        )
        notify_appointment_confirmed(self.appointment)
        notify_appointment_confirmed(self.appointment)
        self.assertEqual(
            Notification.objects.filter(kind=Notification.Kind.APPOINTMENT_CONFIRMED).count(), 2,
        )
        client_notice = Notification.objects.get(
            recipient=self.client_user, kind=Notification.Kind.APPOINTMENT_CONFIRMED,
        )
        self.assertEqual(client_notice.route, f"/appointments/{self.appointment.public_id}")
        self.assertIn("IST", client_notice.body)

        self.appointment.starts_at = timezone.now() + timedelta(minutes=30)
        self.appointment.ends_at = self.appointment.starts_at + timedelta(minutes=30)
        self.appointment.save(update_fields=("starts_at", "ends_at", "updated_at"))
        create_due_appointment_reminders()
        create_due_appointment_reminders()
        self.assertEqual(
            Notification.objects.filter(kind=Notification.Kind.APPOINTMENT_REMINDER_1H).count(), 2,
        )

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_email_delivery_is_audited_without_exposing_private_content(self):
        NotificationPreference.objects.update_or_create(
            user=self.client_user,
            defaults={"email_enabled": True, "push_enabled": False},
        )
        with override_settings(EMAIL_NOTIFICATIONS_ENABLED=False):
            notify_appointment_confirmed(self.appointment)
        notification = Notification.objects.get(
            recipient=self.client_user, kind=Notification.Kind.APPOINTMENT_CONFIRMED,
        )
        delivery = EmailDelivery.objects.get(notification=notification)

        deliver_notification.apply(args=[notification.pk], throw=True)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, EmailDelivery.Status.SENT)
        self.assertEqual(delivery.attempt_count, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("Sensitive", mail.outbox[0].body)

    @override_settings(PUSH_NOTIFICATIONS_ENABLED=True)
    def test_push_receipt_failure_is_audited_and_revokes_dead_device(self):
        device = PushDevice.objects.create(
            user=self.client_user,
            expo_token="ExponentPushToken[receipt-test]",
            platform=PushDevice.Platform.IOS,
            device_id="receipt-phone",
            last_seen_at=timezone.now(),
        )
        notification = Notification.objects.create(
            recipient=self.client_user,
            kind=Notification.Kind.APPOINTMENT_CONFIRMED,
            title="Appointment confirmed",
            body="Open the app for details.",
            route=f"/appointments/{self.appointment.public_id}",
            dedupe_key="receipt-notification",
        )
        delivery = PushDelivery.objects.create(
            notification=notification,
            device=device,
            status=PushDelivery.Status.ACCEPTED,
            provider_ticket_id="ticket-1",
            last_attempt_at=timezone.now() - timedelta(minutes=16),
        )
        with patch(
            "apps.notifications.tasks.ExpoPushProvider.receipts",
            return_value={"ticket-1": {"status": "error", "details": {"error": "DeviceNotRegistered"}}},
        ):
            self.assertEqual(reconcile_push_receipts(), 1)
        delivery.refresh_from_db()
        device.refresh_from_db()
        self.assertEqual(delivery.status, PushDelivery.Status.FAILED)
        self.assertEqual(delivery.last_error_code, "DeviceNotRegistered")
        self.assertIsNotNone(delivery.receipt_checked_at)
        self.assertFalse(device.active)
