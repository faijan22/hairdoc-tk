from django.urls import path

from .views import ClientProgressAllView, ClientProgressDetailView, ClientProgressListCreateView, ClientProgressSubmitView, PrivateProgressPhotoView, ProgressPhotoDetailView, ProgressPhotosView, StaffProgressDetailView, StaffProgressListView, StaffProgressPublishView

app_name = "progress"

urlpatterns = [
    path("progress/", ClientProgressAllView.as_view(), name="client-all"),
    path("consultations/<uuid:case_id>/progress/", ClientProgressListCreateView.as_view(), name="client-case-list-create"),
    path("progress/<uuid:public_id>/", ClientProgressDetailView.as_view(), name="client-detail"),
    path("progress/<uuid:public_id>/submit/", ClientProgressSubmitView.as_view(), name="client-submit"),
    path("progress/<uuid:public_id>/photos/", ProgressPhotosView.as_view(), name="photos"),
    path("progress/<uuid:public_id>/photos/<uuid:photo_id>/", ProgressPhotoDetailView.as_view(), name="photo-detail"),
    path("private-files/progress-photos/<uuid:photo_id>/", PrivateProgressPhotoView.as_view(), name="photo-content"),
    path("staff/progress/", StaffProgressListView.as_view(), name="staff-list"),
    path("staff/progress/<uuid:public_id>/", StaffProgressDetailView.as_view(), name="staff-detail"),
    path("staff/progress/<uuid:public_id>/publish/", StaffProgressPublishView.as_view(), name="staff-publish"),
]
