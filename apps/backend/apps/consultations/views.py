from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ConsultationCase, ConsultationPhoto, ConsultationPhotoAccess
from .photo_services import (
    MAX_PHOTOS_PER_CASE,
    PhotoError,
    complete_photos,
    create_photo,
    delete_photo,
    photo_consent_payload,
    photo_access_allowed,
    resolve_photo_access,
)
from apps.private_media.storage import get_storage_provider
from .selectors import published_services
from .serializers import (
    AnswersPatchSerializer,
    ConsultationCaseSerializer,
    ConsultationServiceDetailSerializer,
    ConsultationServiceListSerializer,
    ConsultationStartSerializer,
    ConsultationPhotoSerializer,
    PhotoUploadSerializer,
    QuestionnaireSerializer,
    answer_payload,
)
from .services import IntakeError, complete_intake, save_answers, start_consultation


class ServiceListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConsultationServiceListSerializer

    def get_queryset(self):
        return published_services()


class ServiceDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConsultationServiceDetailSerializer
    lookup_field = "public_id"

    def get_queryset(self):
        return published_services()


def _client_case(request, public_id):
    return get_object_or_404(
        ConsultationCase.objects.select_related("response__questionnaire", "service"),
        public_id=public_id,
        client=request.user,
    )


class ConsultationListStartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cases = request.user.consultation_cases.select_related("response__questionnaire")
        return Response(ConsultationCaseSerializer(cases, many=True).data)

    def post(self, request):
        serializer = ConsultationStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            case, created = start_consultation(
                request.user,
                serializer.validated_data["service_public_id"],
                serializer.validated_data["timezone"],
            )
        except IntakeError as exc:
            raise ValidationError(exc.details) from None
        return Response(ConsultationCaseSerializer(case).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ConsultationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id):
        return Response(ConsultationCaseSerializer(_client_case(request, public_id)).data)


class ConsultationQuestionnaireView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id):
        case = _client_case(request, public_id)
        questionnaire = case.response.questionnaire
        questionnaire = questionnaire.__class__.objects.prefetch_related("questions__options").get(pk=questionnaire.pk)
        return Response(QuestionnaireSerializer(questionnaire).data)


class ConsultationAnswersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id):
        return Response(answer_payload(_client_case(request, public_id)))

    def patch(self, request, public_id):
        case = _client_case(request, public_id)
        serializer = AnswersPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            case = save_answers(case, serializer.validated_data["answers"])
        except IntakeError as exc:
            raise ValidationError({"answers": exc.details}) from None
        return Response(answer_payload(case))


class ConsultationSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        try:
            case = complete_intake(_client_case(request, public_id))
        except IntakeError as exc:
            raise ValidationError({"answers": exc.details}) from None
        return Response(ConsultationCaseSerializer(case).data)


def _photo_overview(case, viewer):
    return {
        "case_public_id": case.public_id,
        "status": case.status,
        "editable": case.status == ConsultationCase.Status.INTAKE_COMPLETE,
        "max_photos": MAX_PHOTOS_PER_CASE,
        "consent": photo_consent_payload(case.client),
        "photos": ConsultationPhotoSerializer(
            case.photos.select_related("stored_file"), many=True, context={"viewer": viewer},
        ).data,
    }


class ConsultationPhotosView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request, public_id):
        return Response(_photo_overview(_client_case(request, public_id), request.user))

    def post(self, request, public_id):
        case = _client_case(request, public_id)
        serializer = PhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            create_photo(case, serializer.validated_data["file"], serializer.validated_data["category"])
        except PhotoError as exc:
            raise ValidationError(exc.details) from None
        case.refresh_from_db()
        return Response(_photo_overview(case, request.user), status=status.HTTP_201_CREATED)


class ConsultationPhotoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, public_id, photo_id):
        case = _client_case(request, public_id)
        photo = get_object_or_404(
            ConsultationPhoto.objects.select_related("stored_file", "case"), public_id=photo_id, case=case,
        )
        try:
            delete_photo(photo)
        except PhotoError as exc:
            raise ValidationError(exc.details) from None
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConsultationPhotosSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        try:
            case = complete_photos(_client_case(request, public_id))
        except PhotoError as exc:
            raise ValidationError(exc.details) from None
        return Response(ConsultationCaseSerializer(case).data)


class PrivatePhotoContentView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, photo_id):
        try:
            photo, actor, purpose = resolve_photo_access(request.query_params.get("token", ""))
        except PhotoError as exc:
            raise ValidationError(exc.details) from None
        if photo.public_id != photo_id:
            raise ValidationError({"token": ["This private photo link does not match the requested photo."]})
        ConsultationPhotoAccess.objects.create(
            photo=photo,
            actor=actor,
            purpose=purpose,
            request_id=getattr(request, "request_id", ""),
        )
        try:
            content = get_storage_provider().open(photo.stored_file.storage_key)
        except FileNotFoundError:
            raise ValidationError({"photo": ["This private photo is unavailable."]}) from None
        response = FileResponse(content, content_type=photo.stored_file.content_type)
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["Content-Disposition"] = f'inline; filename="{photo.public_id}.jpg"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


def _staff_case_payload(case, viewer):
    answers = case.response.answers.select_related("question").order_by("question__display_order", "id")
    consent_active = photo_access_allowed(case.client)
    return {
        "public_id": case.public_id,
        "status": case.status,
        "service_name": case.service_name,
        "client": {
            "public_id": case.client.public_id,
            "first_name": case.client.first_name,
            "last_name": case.client.last_name,
            "email": case.client.email,
            "phone": case.client.phone,
        },
        "timezone_snapshot": case.timezone_snapshot,
        "hair_profile_snapshot": case.hair_profile_snapshot,
        "intake_completed_at": case.intake_completed_at,
        "photos_completed_at": case.photos_completed_at,
        "updated_at": case.updated_at,
        "answers": [
            {"question": answer.question.prompt, "section": answer.question.section, "value": answer.value}
            for answer in answers
        ],
        "photo_consent_active": consent_active,
        "photos": ConsultationPhotoSerializer(
            case.photos.select_related("stored_file"),
            many=True,
            context={"viewer": viewer} if consent_active else {},
        ).data,
    }


class StaffConsultationListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            limit = min(100, max(1, int(request.query_params.get("limit", "50"))))
        except ValueError:
            raise ValidationError({"limit": ["Use a whole number between 1 and 100."]}) from None
        cases = ConsultationCase.objects.filter(
            status=ConsultationCase.Status.PHOTOS_COMPLETE,
            service__expert=request.user,
        ).select_related("client").prefetch_related("photos").order_by("-photos_completed_at")[:limit]
        return Response([
            {
                "public_id": case.public_id,
                "service_name": case.service_name,
                "client_name": (f"{case.client.first_name} {case.client.last_name}").strip() or case.client.email,
                "client_email": case.client.email,
                "photo_count": len(case.photos.all()),
                "photos_completed_at": case.photos_completed_at,
            }
            for case in cases
        ])


class StaffConsultationDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, public_id):
        case = get_object_or_404(
            ConsultationCase.objects.select_related("client", "response__questionnaire").prefetch_related(
                "response__answers__question", "photos__stored_file",
            ),
            public_id=public_id,
            status=ConsultationCase.Status.PHOTOS_COMPLETE,
            service__expert=request.user,
        )
        return Response(_staff_case_payload(case, request.user))
