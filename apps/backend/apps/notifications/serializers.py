from rest_framework import serializers

from .models import Notification, PushDevice


class PushDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushDevice
        fields = ("public_id", "expo_token", "platform", "device_id", "active", "last_seen_at")
        read_only_fields = ("public_id", "active", "last_seen_at")


class PushDeviceInputSerializer(serializers.Serializer):
    expo_token = serializers.RegexField(r"^(Exponent|Expo)PushToken\[[A-Za-z0-9_-]+\]$", max_length=255)
    platform = serializers.ChoiceField(choices=PushDevice.Platform.choices)
    device_id = serializers.CharField(max_length=120)


class NotificationSerializer(serializers.ModelSerializer):
    conversation_public_id = serializers.UUIDField(source="conversation.public_id", read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = (
            "public_id", "kind", "title", "body", "route",
            "conversation_public_id", "read_at", "created_at",
        )
