from django.urls import path

from .views import (
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    PushDeviceDetailView,
    PushDeviceListCreateView,
)

app_name = "notifications"

urlpatterns = [
    path("push-devices/", PushDeviceListCreateView.as_view(), name="push-device-list-create"),
    path("push-devices/<uuid:public_id>/", PushDeviceDetailView.as_view(), name="push-device-detail"),
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("notifications/<uuid:public_id>/read/", NotificationReadView.as_view(), name="notification-read"),
]
