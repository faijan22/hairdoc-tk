from rest_framework import serializers

from .models import VideoParticipantEvent


class VideoEventSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(choices=(
        VideoParticipantEvent.Type.JOINED,
        VideoParticipantEvent.Type.LEFT,
        VideoParticipantEvent.Type.RECONNECTED,
        VideoParticipantEvent.Type.PERMISSION_DENIED,
    ))
    client_event_id = serializers.CharField(max_length=64)
