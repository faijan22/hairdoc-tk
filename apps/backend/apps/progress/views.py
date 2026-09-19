from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from apps.consultations.models import ConsultationCase
from apps.private_media.storage import get_storage_provider

from .models import ProgressCheckIn, ProgressPhoto, ProgressPhotoAccess
from .photo_services import ProgressPhotoError, create_progress_photo, delete_progress_photo, resolve_progress_photo
from .serializers import ProgressCheckInSerializer, ProgressCheckInUpdateSerializer, ProgressPhotoUploadSerializer, photos_payload
from .services import create_check_in, publish_feedback, save_feedback, submit_check_in, update_check_in


def queryset():
    return ProgressCheckIn.objects.select_related("case__service", "client").prefetch_related("photos__stored_file", "photos__consent_document", "case__photos__stored_file")


def client_check_in(request, public_id):
    return get_object_or_404(queryset(), public_id=public_id, client=request.user)


def staff_check_in(request, public_id):
    return get_object_or_404(queryset(), public_id=public_id, case__service__expert=request.user, status__in=(ProgressCheckIn.Status.SUBMITTED, ProgressCheckIn.Status.REVIEWED))


class ClientProgressListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, case_id):
        items = queryset().filter(case__public_id=case_id, client=request.user)
        return Response(ProgressCheckInSerializer(items, many=True, context={"viewer": request.user}).data)

    def post(self, request, case_id):
        case = get_object_or_404(ConsultationCase.objects.select_related("service"), public_id=case_id, client=request.user)
        item, created = create_check_in(case=case, client=request.user)
        return Response(ProgressCheckInSerializer(queryset().get(pk=item.pk), context={"viewer": request.user}).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ClientProgressAllView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        items = queryset().filter(client=request.user)
        return Response(ProgressCheckInSerializer(items, many=True, context={"viewer": request.user}).data)


class ClientProgressDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, public_id):
        return Response(ProgressCheckInSerializer(client_check_in(request, public_id), context={"viewer": request.user}).data)

    def patch(self, request, public_id):
        item = client_check_in(request, public_id)
        serializer = ProgressCheckInUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = update_check_in(check_in=item, **serializer.validated_data)
        return Response(ProgressCheckInSerializer(queryset().get(pk=item.pk), context={"viewer": request.user}).data)


class ClientProgressSubmitView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, public_id):
        item = submit_check_in(check_in=client_check_in(request, public_id))
        return Response(ProgressCheckInSerializer(queryset().get(pk=item.pk), context={"viewer": request.user}).data)


class ProgressPhotosView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, public_id):
        return Response(photos_payload(client_check_in(request, public_id), request.user))

    def post(self, request, public_id):
        item = client_check_in(request, public_id)
        serializer = ProgressPhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            create_progress_photo(item, serializer.validated_data["file"], serializer.validated_data["category"])
        except ProgressPhotoError as exc:
            raise ValidationError(exc.details) from None
        return Response(photos_payload(client_check_in(request, public_id), request.user), status=status.HTTP_201_CREATED)


class ProgressPhotoDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request, public_id, photo_id):
        item = client_check_in(request, public_id)
        photo = get_object_or_404(ProgressPhoto.objects.select_related("stored_file"), public_id=photo_id, check_in=item)
        try:
            delete_progress_photo(photo)
        except ProgressPhotoError as exc:
            raise ValidationError(exc.details) from None
        return Response(status=status.HTTP_204_NO_CONTENT)


class PrivateProgressPhotoView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request, photo_id):
        try:
            photo, actor, purpose = resolve_progress_photo(request.query_params.get("token", ""))
        except ProgressPhotoError as exc:
            raise ValidationError(exc.details) from None
        if photo.public_id != photo_id:
            raise ValidationError({"token": ["This private photo link does not match the requested photo."]})
        ProgressPhotoAccess.objects.create(photo=photo, actor=actor, purpose=purpose, request_id=getattr(request, "request_id", ""))
        try:
            content = get_storage_provider().open(photo.stored_file.storage_key)
        except FileNotFoundError:
            raise ValidationError({"photo": ["This private photo is unavailable."]}) from None
        response = FileResponse(content, content_type=photo.stored_file.content_type)
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["Content-Disposition"] = f'inline; filename="{photo.public_id}.jpg"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class StaffProgressListView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        items = queryset().filter(case__service__expert=request.user, status__in=(ProgressCheckIn.Status.SUBMITTED, ProgressCheckIn.Status.REVIEWED))[:100]
        return Response(ProgressCheckInSerializer(items, many=True, context={"viewer": request.user, "staff": True}).data)


class StaffProgressDetailView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, public_id):
        return Response(ProgressCheckInSerializer(staff_check_in(request, public_id), context={"viewer": request.user, "staff": True}).data)

    def patch(self, request, public_id):
        feedback = request.data.get("expert_feedback", "")
        if not isinstance(feedback, str) or len(feedback) > 4000:
            raise ValidationError({"expert_feedback": ["Use no more than 4000 characters."]})
        item = save_feedback(check_in=staff_check_in(request, public_id), reviewer=request.user, feedback=feedback)
        return Response(ProgressCheckInSerializer(queryset().get(pk=item.pk), context={"viewer": request.user, "staff": True}).data)


class StaffProgressPublishView(APIView):
    permission_classes = (IsAdminUser,)

    def post(self, request, public_id):
        item = publish_feedback(check_in=staff_check_in(request, public_id), reviewer=request.user)
        return Response(ProgressCheckInSerializer(queryset().get(pk=item.pk), context={"viewer": request.user, "staff": True}).data)
