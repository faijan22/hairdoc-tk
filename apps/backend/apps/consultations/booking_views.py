from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .booking_serializers import (
    AppointmentSerializer,
    AvailabilityExceptionSerializer,
    AvailabilityRuleSerializer,
    BookingInputSerializer,
    CancelInputSerializer,
    RescheduleInputSerializer,
    SlotQuerySerializer,
    WeeklyAvailabilityUpdateSerializer,
)
from .booking_services import (
    BookingError,
    available_slots,
    cancel_appointment,
    create_appointment,
    expire_pending_reservations,
    reschedule_appointment,
    valid_zone,
)
from .models import Appointment, AvailabilityException, AvailabilityRule, ConsultationCase


def _raise_booking(exc):
    raise ValidationError(exc.details) from None


def _client_case(request, public_id):
    return get_object_or_404(
        ConsultationCase.objects.select_related("service"), public_id=public_id, client=request.user,
    )


def _client_appointment(request, public_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("case", "client", "expert"), public_id=public_id, client=request.user,
    )
    expire_pending_reservations(Appointment.objects.filter(pk=appointment.pk))
    appointment.refresh_from_db()
    return appointment


class AvailableSlotsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = SlotQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        case = _client_case(request, data["consultation"])
        try:
            expert, expert_timezone, slots = available_slots(
                case, data["date_from"], data["date_to"], data["timezone"],
            )
        except BookingError as exc:
            _raise_booking(exc)
        return Response({
            "consultation_public_id": case.public_id,
            "service_name": case.service_name,
            "duration_minutes": case.duration_minutes,
            "timezone": data["timezone"],
            "expert_timezone": expert_timezone,
            "expert_name": f"{expert.first_name} {expert.last_name}".strip() or expert.email,
            "slots": [
                {
                    "starts_at": slot["starts_at"],
                    "ends_at": slot["ends_at"],
                    "local_date": slot["local_date"],
                    "local_start": slot["local_start"],
                    "local_end": slot["local_end"],
                }
                for slot in slots
            ],
        })


class AppointmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        appointments = request.user.client_appointments.select_related("case", "client", "expert")
        expire_pending_reservations(appointments)
        return Response(AppointmentSerializer(appointments, many=True).data)

    def post(self, request):
        serializer = BookingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        case = _client_case(request, data["consultation_public_id"])
        try:
            appointment = create_appointment(request.user, case, data["starts_at"], data["timezone"])
        except BookingError as exc:
            _raise_booking(exc)
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)


class AppointmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id):
        return Response(AppointmentSerializer(_client_appointment(request, public_id)).data)


class AppointmentRescheduleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        serializer = RescheduleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            appointment = reschedule_appointment(
                _client_appointment(request, public_id), request.user,
                serializer.validated_data["starts_at"], serializer.validated_data["timezone"],
            )
        except BookingError as exc:
            _raise_booking(exc)
        return Response(AppointmentSerializer(appointment).data)


class AppointmentCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        serializer = CancelInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            appointment = cancel_appointment(
                _client_appointment(request, public_id), request.user, serializer.validated_data.get("reason", ""),
            )
        except BookingError as exc:
            _raise_booking(exc)
        return Response(AppointmentSerializer(appointment).data)


class StaffWeeklyAvailabilityView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        rules = request.user.availability_rules.all()
        timezone_name = rules.values_list("timezone", flat=True).first() or "UTC"
        return Response({"timezone": timezone_name, "rules": AvailabilityRuleSerializer(rules, many=True).data})

    def patch(self, request):
        serializer = WeeklyAvailabilityUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            valid_zone(data["timezone"])
        except BookingError as exc:
            _raise_booking(exc)
        with transaction.atomic():
            request.user.__class__.objects.select_for_update().get(pk=request.user.pk)
            request.user.availability_rules.all().delete()
            AvailabilityRule.objects.bulk_create([
                AvailabilityRule(
                    expert=request.user,
                    weekday=item["weekday"],
                    local_start=item["local_start"],
                    local_end=item["local_end"],
                    timezone=data["timezone"],
                    effective_from=item.get("effective_from"),
                    effective_until=item.get("effective_until"),
                    is_active=item.get("is_active", True),
                )
                for item in data["rules"]
            ])
        rules = request.user.availability_rules.all()
        return Response({"timezone": data["timezone"], "rules": AvailabilityRuleSerializer(rules, many=True).data})


class StaffAvailabilityExceptionListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(AvailabilityExceptionSerializer(request.user.availability_exceptions.all(), many=True).data)

    def post(self, request):
        serializer = AvailabilityExceptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            valid_zone(serializer.validated_data["timezone"])
        except BookingError as exc:
            _raise_booking(exc)
        exception = serializer.save(expert=request.user)
        return Response(AvailabilityExceptionSerializer(exception).data, status=status.HTTP_201_CREATED)


class StaffAvailabilityExceptionDetailView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, public_id):
        exception = get_object_or_404(AvailabilityException, public_id=public_id, expert=request.user)
        exception.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StaffAppointmentListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        appointments = request.user.expert_appointments.select_related("case", "client", "expert")
        expire_pending_reservations(appointments)
        return Response(AppointmentSerializer(appointments, many=True).data)
