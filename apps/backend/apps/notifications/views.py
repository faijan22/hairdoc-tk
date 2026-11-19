from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, PushDevice
from .serializers import NotificationSerializer, PushDeviceInputSerializer, PushDeviceSerializer


class PushDeviceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PushDeviceSerializer(request.user.push_devices.filter(
            active=True,
            session__revoked_at__isnull=True,
            session__expires_at__gt=timezone.now(),
        ), many=True).data)

    def post(self, request):
        serializer = PushDeviceInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        PushDevice.objects.filter(expo_token=values["expo_token"]).exclude(
            user=request.user,
            device_id=values["device_id"],
        ).delete()
        device, _ = PushDevice.objects.update_or_create(
            user=request.user, device_id=values["device_id"],
            defaults={
                **values,
                "session": request.auth,
                "active": True,
                "last_seen_at": timezone.now(),
            },
        )
        return Response(PushDeviceSerializer(device).data, status=status.HTTP_201_CREATED)


class PushDeviceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, public_id):
        device = get_object_or_404(PushDevice, user=request.user, public_id=public_id)
        device.active = False
        device.save(update_fields=("active", "updated_at"))
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = request.user.notifications.select_related("conversation")
        return Response({
            "unread_count": queryset.filter(read_at__isnull=True).count(),
            "results": NotificationSerializer(queryset[:100], many=True).data,
        })


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        notification = get_object_or_404(Notification, recipient=request.user, public_id=public_id)
        if not notification.read_at:
            notification.read_at = timezone.now()
            notification.save(update_fields=("read_at", "updated_at"))
        return Response(NotificationSerializer(notification).data)


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        now = timezone.now()
        request.user.notifications.filter(read_at__isnull=True).update(read_at=now, updated_at=now)
        return Response({"unread_count": 0})
