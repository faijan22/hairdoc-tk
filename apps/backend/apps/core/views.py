from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.consultations.booking_serializers import AppointmentSerializer
from apps.consultations.booking_services import expire_pending_reservations
from apps.consultations.models import Appointment, ConsultationCase
from apps.consultations.selectors import published_services
from apps.consultations.serializers import ConsultationCaseSerializer, ConsultationServiceListSerializer
from apps.content.selectors import published_content
from apps.content.serializers import ContentItemListSerializer


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request) -> Response:
        return Response(
            {
                "status": "ok",
                "service": "hairdoc-tk-api",
                "api_version": "v1",
            }
        )


class HomeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request) -> Response:
        active_case = None
        next_appointment = None

        if request.user.is_authenticated:
            active_case = (
                request.user.consultation_cases
                .exclude(status=ConsultationCase.Status.CANCELLED)
                .select_related("response__questionnaire")
                .order_by("-updated_at")
                .first()
            )
            client_appointments = request.user.client_appointments.select_related("case", "client", "expert")
            expire_pending_reservations(client_appointments)
            next_appointment = (
                client_appointments
                .filter(
                    status__in=(Appointment.Status.PAYMENT_PENDING, Appointment.Status.CONFIRMED),
                    ends_at__gt=timezone.now(),
                )
                .order_by("starts_at")
                .first()
            )

        services = published_services() if request.user.is_authenticated else []
        return Response({
            "services": ConsultationServiceListSerializer(services, many=True).data,
            "active_consultation": ConsultationCaseSerializer(active_case).data if active_case else None,
            "next_appointment": AppointmentSerializer(next_appointment).data if next_appointment else None,
            "content": ContentItemListSerializer(published_content()[:3], many=True).data,
        })
