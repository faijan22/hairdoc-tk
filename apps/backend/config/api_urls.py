from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
    path("content/", include("apps.content.urls")),
    path("", include("apps.consultations.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.messaging.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.video.urls")),
    path("", include("apps.coaching.urls")),
    path("", include("apps.progress.urls")),
]
