from rest_framework import serializers

from .models import CoachingPlan, CoachingPlanSection, Recommendation


class CoachingPlanSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachingPlanSection
        fields = ("public_id", "title", "body", "display_order")


class RecommendationSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Recommendation
        fields = ("public_id", "category", "category_label", "title", "guidance", "external_url", "display_order")


class CoachingPlanSerializer(serializers.ModelSerializer):
    case_public_id = serializers.UUIDField(source="case.public_id", read_only=True)
    client_name = serializers.SerializerMethodField()
    service_name = serializers.CharField(source="case.service_name", read_only=True)
    sections = CoachingPlanSectionSerializer(many=True, read_only=True)
    recommendations = RecommendationSerializer(many=True, read_only=True)

    class Meta:
        model = CoachingPlan
        fields = ("public_id", "case_public_id", "client_name", "service_name", "version", "title", "summary", "status", "published_at", "created_at", "updated_at", "sections", "recommendations")

    def get_client_name(self, obj):
        return f"{obj.case.client.first_name} {obj.case.client.last_name}".strip() or obj.case.client.email


class SectionInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=160)
    body = serializers.CharField(max_length=4000)


class RecommendationInputSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=Recommendation.Category.choices)
    title = serializers.CharField(max_length=160)
    guidance = serializers.CharField(max_length=2000)
    external_url = serializers.URLField(max_length=500, required=False, allow_blank=True, default="")


class CoachingPlanCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=180, default="Your care plan")
    summary = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class CoachingPlanUpdateSerializer(CoachingPlanCreateSerializer):
    sections = SectionInputSerializer(many=True, allow_empty=False)
    recommendations = RecommendationInputSerializer(many=True, required=False, default=list)
