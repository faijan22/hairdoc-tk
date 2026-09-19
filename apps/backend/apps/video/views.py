from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.consultations.models import Appointment

from .providers.base import VideoProviderError
from .serializers import VideoEventSerializer
from .services import VideoAccessError, complete_video, join_video, record_event, video_state


def participant_appointment(request, public_id):
    return get_object_or_404(
        Appointment.objects.select_related("case", "client", "expert", "video_session").filter(
            Q(client=request.user) | Q(expert=request.user), public_id=public_id,
        )
    )


def raise_video_error(exc):
    if isinstance(exc, VideoAccessError) and exc.code == "not_found":
        raise NotFound() from None
    message = exc.message if isinstance(exc, VideoAccessError) else str(exc)
    code = exc.code if isinstance(exc, VideoAccessError) else "provider_error"
    raise ValidationError({"video": [message], "reason_code": [code]}) from None


class VideoStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id):
        return Response(video_state(participant_appointment(request, public_id), request.user))


class VideoJoinView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "video_join"

    def post(self, request, public_id):
        appointment = participant_appointment(request, public_id)
        try:
            session, grant = join_video(appointment, request.user)
        except (VideoAccessError, VideoProviderError) as exc:
            raise_video_error(exc)
        return Response({
            "session_public_id": session.public_id,
            "join_url": grant.url,
            "expires_at": grant.expires_at,
        })


class VideoEventView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        serializer = VideoEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            event = record_event(
                participant_appointment(request, public_id), request.user,
                serializer.validated_data["event_type"], serializer.validated_data["client_event_id"],
            )
        except VideoAccessError as exc:
            raise_video_error(exc)
        return Response({"event_public_id": event.public_id, "event_type": event.event_type})


class VideoCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        appointment = participant_appointment(request, public_id)
        try:
            complete_video(appointment, request.user)
        except VideoAccessError as exc:
            raise_video_error(exc)
        appointment.refresh_from_db()
        return Response(video_state(appointment, request.user))

