from django.urls import path

from .views import VideoCompleteView, VideoEventView, VideoJoinView, VideoStatusView

urlpatterns = [
    path("appointments/<uuid:public_id>/video/", VideoStatusView.as_view(), name="video-status"),
    path("appointments/<uuid:public_id>/video/join/", VideoJoinView.as_view(), name="video-join"),
    path("appointments/<uuid:public_id>/video/events/", VideoEventView.as_view(), name="video-event"),
    path("appointments/<uuid:public_id>/video/complete/", VideoCompleteView.as_view(), name="video-complete"),
]
