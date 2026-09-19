from rest_framework import serializers

from .models import Order, OrderItem, Payment, Refund


class OrderCreateSerializer(serializers.Serializer):
    appointment_public_id = serializers.UUIDField()


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("description", "quantity", "unit_amount", "total_amount")


class OrderSerializer(serializers.ModelSerializer):
    appointment_public_id = serializers.UUIDField(source="appointment.public_id", read_only=True)
    consultation_public_id = serializers.UUIDField(source="appointment.case.public_id", read_only=True)
    service_name = serializers.CharField(source="appointment.case.service_name", read_only=True)
    appointment_starts_at = serializers.DateTimeField(source="appointment.starts_at", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    payment_public_id = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "public_id", "appointment_public_id", "consultation_public_id", "service_name",
            "appointment_starts_at", "status", "status_label", "payment_public_id", "payment_status",
            "subtotal_amount", "total_amount",
            "currency", "paid_at", "items", "created_at", "updated_at",
        )

    def get_payment_public_id(self, obj):
        return obj.payment.public_id if hasattr(obj, "payment") else None

    def get_payment_status(self, obj):
        return obj.payment.status if hasattr(obj, "payment") else None


class RefundSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Refund
        fields = ("public_id", "amount", "currency", "status", "status_label", "reason", "created_at")


class PaymentSerializer(serializers.ModelSerializer):
    order_public_id = serializers.UUIDField(source="order.public_id", read_only=True)
    appointment_public_id = serializers.UUIDField(source="order.appointment.public_id", read_only=True)
    consultation_public_id = serializers.UUIDField(source="order.appointment.case.public_id", read_only=True)
    service_name = serializers.CharField(source="order.appointment.case.service_name", read_only=True)
    appointment_starts_at = serializers.DateTimeField(source="order.appointment.starts_at", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    receipt_number = serializers.SerializerMethodField()
    refunds = RefundSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = (
            "public_id", "order_public_id", "appointment_public_id", "consultation_public_id",
            "service_name", "appointment_starts_at", "provider", "status", "status_label",
            "amount", "currency", "receipt_number", "paid_at", "failure_message", "refunds",
            "created_at", "updated_at",
        )

    def get_receipt_number(self, obj):
        return f"HDTK-{str(obj.public_id).split('-')[0].upper()}"


class StaffPaymentSerializer(PaymentSerializer):
    client_name = serializers.SerializerMethodField()
    client_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta(PaymentSerializer.Meta):
        fields = PaymentSerializer.Meta.fields + ("client_name", "client_email")

    def get_client_name(self, obj):
        user = obj.user
        return f"{user.first_name} {user.last_name}".strip() or user.email


class CheckoutSerializer(serializers.Serializer):
    payment = PaymentSerializer()
    checkout_url = serializers.URLField()
    expires_at = serializers.DateTimeField()
