from rest_framework import serializers

from django.urls import reverse

from .models import (
    ConsultationCase,
    ConsultationPhoto,
    ConsultationService,
    QuestionOption,
    Questionnaire,
    QuestionnaireQuestion,
)
from .photo_services import issue_photo_access_token


class ConsultationServiceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationService
        fields = ("public_id", "name", "slug", "short_description", "duration_minutes", "price_amount", "currency")


class ConsultationServiceDetailSerializer(ConsultationServiceListSerializer):
    class Meta(ConsultationServiceListSerializer.Meta):
        fields = ConsultationServiceListSerializer.Meta.fields + ("description",)


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ("value", "label")


class QuestionnaireQuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)

    class Meta:
        model = QuestionnaireQuestion
        fields = (
            "key", "section", "prompt", "help_text", "type", "required", "placeholder",
            "max_length", "show_if_question_key", "show_if_value", "options",
        )


class QuestionnaireSerializer(serializers.ModelSerializer):
    questions = QuestionnaireQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Questionnaire
        fields = ("public_id", "version", "title", "introduction", "questions")


class ConsultationCaseSerializer(serializers.ModelSerializer):
    questionnaire_version = serializers.IntegerField(source="response.questionnaire.version", read_only=True)

    class Meta:
        model = ConsultationCase
        fields = (
            "public_id", "status", "service_name", "duration_minutes", "price_amount", "currency",
            "timezone_snapshot", "hair_profile_snapshot", "questionnaire_version", "created_at", "updated_at",
            "intake_completed_at",
            "photos_completed_at",
        )


class ConsultationStartSerializer(serializers.Serializer):
    service_public_id = serializers.UUIDField()
    timezone = serializers.CharField(max_length=64)


class AnswerInputSerializer(serializers.Serializer):
    question_key = serializers.SlugField(max_length=80)
    value = serializers.JSONField(required=False, allow_null=True)


class AnswersPatchSerializer(serializers.Serializer):
    answers = AnswerInputSerializer(many=True, allow_empty=False)


class AnswersSerializer(serializers.Serializer):
    case_public_id = serializers.UUIDField()
    status = serializers.CharField()
    answers = serializers.DictField()


class ConsultationPhotoSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    content_path = serializers.SerializerMethodField()
    width = serializers.IntegerField(source="stored_file.width", read_only=True)
    height = serializers.IntegerField(source="stored_file.height", read_only=True)
    byte_size = serializers.IntegerField(source="stored_file.byte_size", read_only=True)

    class Meta:
        model = ConsultationPhoto
        fields = (
            "public_id", "category", "category_label", "width", "height", "byte_size",
            "created_at", "content_path",
        )

    def get_content_path(self, obj):
        viewer = self.context.get("viewer")
        if not viewer:
            return None
        token = issue_photo_access_token(obj, viewer)
        return f'{reverse("consultations:photo-content", kwargs={"photo_id": obj.public_id})}?token={token}'


class PhotoUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    category = serializers.ChoiceField(choices=ConsultationPhoto.Category.choices)


def answer_payload(case: ConsultationCase):
    return {
        "case_public_id": case.public_id,
        "status": case.status,
        "answers": {answer.question.key: answer.value for answer in case.response.answers.select_related("question")},
    }
