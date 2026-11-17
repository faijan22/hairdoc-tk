from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.services import create_device_session
from apps.consultations.models import (
    Appointment,
    AppointmentStatusHistory,
    AvailabilityRule,
    ConsultationCase,
    ConsultationService,
)
from apps.messaging.models import Conversation
from apps.payments.models import Order


class BookingApiTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            "client@example.com", "HairDoc!2026Strong", is_email_verified=True,
        )
        self.other_user = User.objects.create_user(
            "other@example.com", "HairDoc!2026Strong", is_email_verified=True,
        )
        self.tk = User.objects.create_user(
            "tk@example.com", "HairDoc!2026Strong", first_name="TK", is_email_verified=True, is_staff=True,
        )
        self.service = ConsultationService.objects.create(
            name="Booking consultation", slug="booking-consultation", short_description="Book with TK.",
            description="Book with TK.", duration_minutes=45, price_amount="80", currency="GBP",
            status=ConsultationService.Status.PUBLISHED, published_at=timezone.now(), expert=self.tk,
        )
        self.case = self.make_case(self.client_user)
        self.other_case = self.make_case(self.other_user)
        self.day = self.next_weekday(0)
        AvailabilityRule.objects.create(
            expert=self.tk, weekday=0, local_start=time(9), local_end=time(12), timezone="Europe/London",
        )
        self.authorize(self.client_user)

    def make_case(self, user):
        return ConsultationCase.objects.create(
            client=user, service=self.service, status=ConsultationCase.Status.PHOTOS_COMPLETE,
            timezone_snapshot="Europe/London", service_name=self.service.name, duration_minutes=45,
            price_amount="80", currency="GBP", intake_completed_at=timezone.now(), photos_completed_at=timezone.now(),
        )

    def authorize(self, user):
        access, _, _ = create_device_session(user, "Test device")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def next_weekday(self, weekday):
        current = timezone.now().date() + timedelta(days=1)
        return current + timedelta(days=(weekday - current.weekday()) % 7)

    def slots(self, case=None, day=None, timezone_name="Europe/London"):
        case = case or self.case
        day = day or self.day
        return self.client.get(reverse("consultations:available-slots"), {
            "consultation": case.public_id,
            "date_from": day.isoformat(),
            "date_to": day.isoformat(),
            "timezone": timezone_name,
        })

    def book(self, case=None, starts_at=None):
        case = case or self.case
        starts_at = starts_at or self.slots(case).json()["slots"][0]["starts_at"]
        return self.client.post(reverse("consultations:appointment-list-create"), {
            "consultation_public_id": str(case.public_id),
            "starts_at": starts_at,
            "timezone": "Europe/London",
        }, format="json")

    def test_slots_are_server_generated_timezone_safe_and_photo_complete_scoped(self):
        response = self.slots()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["duration_minutes"], 45)
        self.assertEqual(response.json()["expert_timezone"], "Europe/London")
        self.assertEqual(len(response.json()["slots"]), 10)
        first = datetime.fromisoformat(response.json()["slots"][0]["local_start"])
        self.assertEqual((first.hour, first.minute), (9, 0))

        self.case.status = ConsultationCase.Status.INTAKE_COMPLETE
        self.case.save(update_fields=("status", "updated_at"))
        self.assertEqual(self.slots().status_code, 400)
        self.case.status = ConsultationCase.Status.PHOTOS_COMPLETE
        self.case.save(update_fields=("status", "updated_at"))

        self.authorize(self.other_user)
        self.assertEqual(self.slots(self.case).status_code, 404)
        self.assertEqual(self.slots(self.other_case, timezone_name="Not/AZone").status_code, 400)

    def test_booking_rejects_forged_and_overlapping_slots_then_cancel_releases(self):
        slot = self.slots().json()["slots"][0]
        forged = datetime.fromisoformat(slot["starts_at"]) + timedelta(minutes=7)
        self.assertEqual(self.book(starts_at=forged.isoformat()).status_code, 400)

        booked = self.book(starts_at=slot["starts_at"])
        self.assertEqual(booked.status_code, 201)
        self.assertEqual(booked.json()["status"], Appointment.Status.PAYMENT_PENDING)
        self.assertIsNotNone(booked.json()["reservation_expires_at"])
        self.assertEqual(AppointmentStatusHistory.objects.count(), 1)
        self.assertEqual(self.book(starts_at=slot["starts_at"]).status_code, 400)

        self.authorize(self.other_user)
        self.assertEqual(self.book(self.other_case, slot["starts_at"]).status_code, 400)

        self.authorize(self.client_user)
        appointment_id = booked.json()["public_id"]
        cancel = self.client.post(
            reverse("consultations:appointment-cancel", kwargs={"public_id": appointment_id}),
            {"reason": "Need another day."}, format="json",
        )
        self.assertEqual(cancel.status_code, 200)
        self.assertEqual(cancel.json()["status"], Appointment.Status.CANCELLED)

        self.authorize(self.other_user)
        self.assertEqual(self.book(self.other_case, slot["starts_at"]).status_code, 201)

    def test_reschedule_and_expired_hold_lifecycle(self):
        slots = self.slots().json()["slots"]
        booked = self.book(starts_at=slots[0]["starts_at"]).json()
        moved = self.client.post(
            reverse("consultations:appointment-reschedule", kwargs={"public_id": booked["public_id"]}),
            {"starts_at": slots[4]["starts_at"], "timezone": "Europe/London"}, format="json",
        )
        self.assertEqual(moved.status_code, 200)
        self.assertEqual(moved.json()["starts_at"], slots[4]["starts_at"])
        self.assertEqual(AppointmentStatusHistory.objects.count(), 2)

        appointment = Appointment.objects.get(public_id=booked["public_id"])
        appointment.reservation_expires_at = timezone.now() - timedelta(seconds=1)
        appointment.save(update_fields=("reservation_expires_at", "updated_at"))
        detail = self.client.get(reverse("consultations:appointment-detail", kwargs={"public_id": appointment.public_id}))
        self.assertEqual(detail.json()["status"], Appointment.Status.EXPIRED)
        self.assertEqual(
            AppointmentStatusHistory.objects.filter(to_status=Appointment.Status.EXPIRED).count(), 1,
        )
        starts = {item["starts_at"] for item in self.slots().json()["slots"]}
        self.assertIn(slots[4]["starts_at"], starts)

    def test_free_consultation_confirms_without_payment_provider_and_opens_private_conversation(self):
        self.case.price_amount = "0.00"
        self.case.save(update_fields=("price_amount", "updated_at"))

        booked = self.book()

        self.assertEqual(booked.status_code, 201)
        self.assertEqual(booked.json()["status"], Appointment.Status.CONFIRMED)
        self.assertIsNone(booked.json()["reservation_expires_at"])
        self.assertEqual(Order.objects.count(), 0)
        conversation = Conversation.objects.get(consultation=self.case)
        self.assertEqual(conversation.members.count(), 2)
        self.assertSetEqual(
            set(conversation.members.values_list("user__email", flat=True)),
            {self.client_user.email, self.tk.email},
        )
        self.assertEqual(
            AppointmentStatusHistory.objects.get(appointment__case=self.case).to_status,
            Appointment.Status.CONFIRMED,
        )

    def test_staff_manages_weekly_hours_exceptions_and_reviews_appointments(self):
        self.authorize(self.tk)
        weekly_url = reverse("consultations:staff-availability-weekly")
        weekly = self.client.patch(weekly_url, {
            "timezone": "Europe/London",
            "rules": [
                {"weekday": 0, "local_start": "10:00", "local_end": "13:00", "is_active": True},
                {"weekday": 2, "local_start": "09:00", "local_end": "12:00", "is_active": True},
            ],
        }, format="json")
        self.assertEqual(weekly.status_code, 200)
        self.assertEqual(len(weekly.json()["rules"]), 2)
        self.assertEqual(weekly.json()["rules"][0]["local_start"], "10:00")

        exceptions_url = reverse("consultations:staff-availability-exceptions")
        blocked = self.client.post(exceptions_url, {
            "date": self.day.isoformat(), "kind": "BLOCKED", "local_start": None,
            "local_end": None, "timezone": "Europe/London", "note": "Away",
        }, format="json")
        self.assertEqual(blocked.status_code, 201)

        self.authorize(self.client_user)
        self.assertEqual(self.slots().json()["slots"], [])

        self.authorize(self.tk)
        self.assertEqual(self.client.get(reverse("consultations:staff-appointment-list")).status_code, 200)
        self.assertEqual(
            self.client.delete(reverse(
                "consultations:staff-availability-exception-detail",
                kwargs={"public_id": blocked.json()["public_id"]},
            )).status_code,
            204,
        )

        self.authorize(self.client_user)
        first = datetime.fromisoformat(self.slots().json()["slots"][0]["local_start"])
        self.assertEqual((first.hour, first.minute), (10, 0))

    def test_nonstaff_cannot_manage_availability_and_dst_gap_is_not_offered(self):
        self.assertEqual(self.client.get(reverse("consultations:staff-availability-weekly")).status_code, 403)
        year = timezone.now().year + 1
        march_end = date(year, 3, 31)
        dst_day = march_end - timedelta(days=(march_end.weekday() - 6) % 7)
        AvailabilityRule.objects.all().delete()
        AvailabilityRule.objects.create(
            expert=self.tk, weekday=6, local_start=time(1), local_end=time(3), timezone="Europe/London",
        )
        response = self.slots(day=dst_day)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slots"], [])
