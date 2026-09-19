from rest_framework import serializers

from .models import ContentItem


class ContentItemListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentItem
        fields = ("public_id", "type", "title", "slug", "summary", "external_url", "published_at")


class ContentItemDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentItem
        fields = ("public_id", "type", "title", "slug", "summary", "body", "external_url", "published_at")

