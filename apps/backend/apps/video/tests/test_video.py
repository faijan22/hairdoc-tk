from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.services import create_device_session
from apps.consultations.models import Appointment, ConsultationCase, ConsultationService
from apps.video.models import VideoParticipantEvent, VideoSession
from apps.video.providers.base import JoinGrant


class FakeVideoProvider:
    code = "FAKE"
    created = []
    closed = []

    @property
    def is_configured(self):
        return True

    def create_room(self, *, room_id, available_from, expires_at):
        self.created.append(room_id)

    def issue_join_grant(self, *, room_id, user_id, user_name, is_owner, available_from, expires_at):
        return JoinGrant(url=f"https://video.test/{room_id}?t=short-lived", expires_at=expires_at)

    def close_room(self, *, room_id):
        self.closed.append(room_id)


@override_settings(VIDEO_PROVIDER_BACKEND="apps.video.tests.test_video.FakeVideoProvider")
class VideoApiTests(APITestCase):
    def setUp(self):
        FakeVideoProvider.created.clear(); FakeVideoProvider.closed.clear()
        self.user = User.objects.create_user("client@example.com", "HairDoc!2026Strong", is_email_verified=True)
        self.other = User.objects.create_user("other@example.com", "HairDoc!2026Strong", is_email_verified=True)
        self.tk = User.objects.create_user("tk@example.com", "HairDoc!2026Strong", first_name="TK", is_email_verified=True, is_staff=True)
        service = ConsultationService.objects.create(
            name="Video consultation", slug="video-consultation", short_description="Meet TK.",
            description="Meet TK.", duration_minutes=30, price_amount="60", currency="GBP",
            status=ConsultationService.Status.PUBLISHED, published_at=timezone.now(), expert=self.tk,
        )
        case = ConsultationCase.objects.create(
            client=self.user, service=service, status=ConsultationCase.Status.PHOTOS_COMPLETE,
            timezone_snapshot="Europe/London", service_name=service.name, duration_minutes=30,
            price_amount="60", currency="GBP", intake_completed_at=timezone.now(), photos_completed_at=timezone.now(),
        )
        self.appointment = Appointment.objects.create(
            case=case, client=self.user, expert=self.tk,
            starts_at=timezone.now() + timedelta(minutes=5), ends_at=timezone.now() + timedelta(minutes=35),
            status=Appointment.Status.CONFIRMED, client_timezone="Europe/London", expert_timezone="Europe/London",
        )
        self.authorize(self.user)

    def authorize(self, user):
        access, _, _ = create_device_session(user, "Video test")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def url(self, name):
        return reverse(name, kwargs={"public_id": self.appointment.public_id})

    def test_status_and_join_are_participant_scoped_and_room_is_reused(self):
        status = self.client.get(self.url("video-status"))
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.json()["can_join"])
        self.assertEqual(status.json()["participant_role"], "CLIENT")

        first = self.client.post(self.url("video-join"), {}, format="json")
        second = self.client.post(self.url("video-join"), {}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["join_url"].startswith("https://video.test/"))
        self.assertEqual(VideoSession.objects.count(), 1)
        self.assertEqual(len(FakeVideoProvider.created), 1)
        self.assertEqual(VideoParticipantEvent.objects.filter(event_type="TOKEN_ISSUED").count(), 2)
        self.assertFalse(any(field.name == "token" for field in VideoSession._meta.fields))

        self.authorize(self.other)
        self.assertEqual(self.client.get(self.url("video-status")).status_code, 404)
        self.assertEqual(self.client.post(self.url("video-join"), {}, format="json").status_code, 404)

    def test_join_window_and_confirmed_status_fail_closed(self):
        self.appointment.starts_at = timezone.now() + timedelta(hours=2)
        self.appointment.ends_at = self.appointment.starts_at + timedelta(minutes=30)
        self.appointment.save(update_fields=("starts_at", "ends_at", "updated_at"))
        response = self.client.post(self.url("video-join"), {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["details"]["reason_code"], ["too_early"])

        self.appointment.status = Appointment.Status.PAYMENT_PENDING
        self.appointment.starts_at = timezone.now() + timedelta(minutes=5)
        self.appointment.ends_at = timezone.now() + timedelta(minutes=35)
        self.appointment.save(update_fields=("status", "starts_at", "ends_at", "updated_at"))
        self.assertEqual(self.client.post(self.url("video-join"), {}, format="json").status_code, 400)

    def test_events_are_idempotent_and_only_expert_completes(self):
        self.assertEqual(self.client.post(self.url("video-join"), {}, format="json").status_code, 200)
        event = {"event_type": "JOINED", "client_event_id": "device-event-1"}
        self.assertEqual(self.client.post(self.url("video-event"), event, format="json").status_code, 200)
        self.assertEqual(self.client.post(self.url("video-event"), event, format="json").status_code, 200)
        self.assertEqual(VideoParticipantEvent.objects.filter(client_event_id="device-event-1").count(), 1)
        self.assertEqual(VideoSession.objects.get().status, VideoSession.Status.ACTIVE)

        self.assertEqual(self.client.post(self.url("video-complete"), {}, format="json").status_code, 400)
        self.authorize(self.tk)
        completed = self.client.post(self.url("video-complete"), {}, format="json")
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["reason_code"], "completed")
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)

    def test_cancelling_appointment_cancels_existing_video_session(self):
        self.client.post(self.url("video-join"), {}, format="json")
        cancelled = self.client.post(
            reverse("consultations:appointment-cancel", kwargs={"public_id": self.appointment.public_id}),
            {"reason": "Cannot attend"}, format="json",
        )
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(VideoSession.objects.get().status, VideoSession.Status.CANCELLED)
