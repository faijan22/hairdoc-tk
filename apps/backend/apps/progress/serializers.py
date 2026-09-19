from django.urls import reverse
from rest_framework import serializers

from apps.consultations.photo_services import photo_access_allowed
from apps.consultations.serializers import ConsultationPhotoSerializer

from .models import ProgressCheckIn, ProgressPhoto
from .photo_services import MAX_PHOTOS_PER_CHECK_IN, issue_progress_photo_token


class ProgressPhotoSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    width = serializers.IntegerField(source="stored_file.width", read_only=True)
    height = serializers.IntegerField(source="stored_file.height", read_only=True)
    content_path = serializers.SerializerMethodField()

    class Meta:
        model = ProgressPhoto
        fields = ("public_id", "category", "category_label", "width", "height", "created_at", "content_path")

    def get_content_path(self, obj):
        viewer = self.context.get("viewer")
        if not viewer:
            return None
        token = issue_progress_photo_token(obj, viewer)
        return f'{reverse("progress:photo-content", kwargs={"photo_id": obj.public_id})}?token={token}'


class ProgressCheckInSerializer(serializers.ModelSerializer):
    case_public_id = serializers.UUIDField(source="case.public_id", read_only=True)
    service_name = serializers.CharField(source="case.service_name", read_only=True)
    client_name = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()
    baseline_photos = serializers.SerializerMethodField()
    expert_feedback = serializers.SerializerMethodField()

    class Meta:
        model = ProgressCheckIn
        fields = ("public_id", "case_public_id", "service_name", "client_name", "sequence", "status", "summary", "wins", "challenges", "routine_adherence", "questions_for_tk", "submitted_at", "expert_feedback", "feedback_published_at", "created_at", "updated_at", "photos", "baseline_photos")

    def get_client_name(self, obj):
        return f"{obj.client.first_name} {obj.client.last_name}".strip() or obj.client.email

    def get_photos(self, obj):
        return ProgressPhotoSerializer(obj.photos.all(), many=True, context={"viewer": self.context.get("viewer")}).data

    def get_baseline_photos(self, obj):
        viewer = self.context.get("viewer")
        if not viewer or not photo_access_allowed(obj.client):
            return []
        return ConsultationPhotoSerializer(obj.case.photos.all(), many=True, context={"viewer": viewer}).data

    def get_expert_feedback(self, obj):
        if self.context.get("staff") or obj.feedback_published_at:
            return obj.expert_feedback
        return ""


class ProgressCheckInUpdateSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    wins = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    challenges = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    routine_adherence = serializers.IntegerField(min_value=1, max_value=5, required=False, allow_null=True, default=None)
    questions_for_tk = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class ProgressPhotoUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    category = serializers.ChoiceField(choices=ProgressPhoto.Category.choices)


def photos_payload(check_in, viewer):
    from apps.consultations.photo_services import photo_consent_payload
    return {"check_in_public_id": check_in.public_id, "editable": check_in.status == ProgressCheckIn.Status.DRAFT, "max_photos": MAX_PHOTOS_PER_CHECK_IN, "consent": photo_consent_payload(check_in.client), "photos": ProgressPhotoSerializer(check_in.photos.select_related("stored_file", "consent_document"), many=True, context={"viewer": viewer}).data}
