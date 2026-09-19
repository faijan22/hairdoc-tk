from rest_framework import serializers

from .models import Appointment, AvailabilityException, AvailabilityRule


class SlotQuerySerializer(serializers.Serializer):
    consultation = serializers.UUIDField()
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    timezone = serializers.CharField(max_length=64)


class BookingInputSerializer(serializers.Serializer):
    consultation_public_id = serializers.UUIDField()
    starts_at = serializers.DateTimeField()
    timezone = serializers.CharField(max_length=64)


class RescheduleInputSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    timezone = serializers.CharField(max_length=64)


class CancelInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True)


class AppointmentSerializer(serializers.ModelSerializer):
    consultation_public_id = serializers.UUIDField(source="case.public_id", read_only=True)
    service_name = serializers.CharField(source="case.service_name", read_only=True)
    client_name = serializers.SerializerMethodField()
    client_email = serializers.EmailField(source="client.email", read_only=True)
    expert_name = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Appointment
        fields = (
            "public_id", "consultation_public_id", "service_name", "client_name", "client_email",
            "expert_name", "starts_at", "ends_at", "status", "status_label", "client_timezone",
            "expert_timezone", "reservation_expires_at", "cancelled_at", "cancel_reason", "created_at", "updated_at",
        )

    def get_client_name(self, obj):
        return f"{obj.client.first_name} {obj.client.last_name}".strip() or obj.client.email

    def get_expert_name(self, obj):
        return f"{obj.expert.first_name} {obj.expert.last_name}".strip() or obj.expert.email


class AvailabilityRuleSerializer(serializers.ModelSerializer):
    timezone = serializers.CharField(max_length=64, required=False)
    local_start = serializers.TimeField(format="%H:%M", input_formats=("%H:%M",))
    local_end = serializers.TimeField(format="%H:%M", input_formats=("%H:%M",))

    class Meta:
        model = AvailabilityRule
        fields = (
            "public_id", "weekday", "local_start", "local_end", "timezone",
            "effective_from", "effective_until", "is_active",
        )
        read_only_fields = ("public_id",)

    def validate_weekday(self, value):
        if value not in range(7):
            raise serializers.ValidationError("Weekday must be between 0 and 6.")
        return value

    def validate(self, attrs):
        if attrs["local_start"] >= attrs["local_end"]:
            raise serializers.ValidationError({"local_end": "End time must be after start time."})
        if attrs.get("effective_from") and attrs.get("effective_until") and attrs["effective_until"] < attrs["effective_from"]:
            raise serializers.ValidationError({"effective_until": "End date cannot be before start date."})
        return attrs


class WeeklyAvailabilityUpdateSerializer(serializers.Serializer):
    timezone = serializers.CharField(max_length=64)
    rules = AvailabilityRuleSerializer(many=True)

    def validate_rules(self, rules):
        intervals = [(item["weekday"], item["local_start"], item["local_end"]) for item in rules]
        if len(intervals) != len(set(intervals)):
            raise serializers.ValidationError("Do not submit duplicate weekly intervals.")
        return rules


class AvailabilityExceptionSerializer(serializers.ModelSerializer):
    local_start = serializers.TimeField(
        format="%H:%M", input_formats=("%H:%M",), required=False, allow_null=True,
    )
    local_end = serializers.TimeField(
        format="%H:%M", input_formats=("%H:%M",), required=False, allow_null=True,
    )

    class Meta:
        model = AvailabilityException
        fields = ("public_id", "date", "kind", "local_start", "local_end", "timezone", "note")
        read_only_fields = ("public_id",)

    def validate(self, attrs):
        start, end = attrs.get("local_start"), attrs.get("local_end")
        if (start is None) != (end is None):
            raise serializers.ValidationError("Provide both start and end times.")
        if start and start >= end:
            raise serializers.ValidationError({"local_end": "End time must be after start time."})
        if attrs.get("kind") == AvailabilityException.Kind.EXTRA and start is None:
            raise serializers.ValidationError({"local_start": "Extra availability requires times."})
        return attrs
