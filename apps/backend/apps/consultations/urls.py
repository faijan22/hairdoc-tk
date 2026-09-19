from django.urls import path

from .booking_views import (
    AppointmentCancelView,
    AppointmentDetailView,
    AppointmentListCreateView,
    AppointmentRescheduleView,
    AvailableSlotsView,
    StaffAppointmentListView,
    StaffAvailabilityExceptionDetailView,
    StaffAvailabilityExceptionListCreateView,
    StaffWeeklyAvailabilityView,
)

from .views import (
    ConsultationAnswersView,
    ConsultationDetailView,
    ConsultationListStartView,
    ConsultationPhotoDetailView,
    ConsultationPhotosSubmitView,
    ConsultationPhotosView,
    ConsultationQuestionnaireView,
    ConsultationSubmitView,
    PrivatePhotoContentView,
    ServiceDetailView,
    ServiceListView,
    StaffConsultationDetailView,
    StaffConsultationListView,
)

app_name = "consultations"

urlpatterns = [
    path("consultation-services/", ServiceListView.as_view(), name="service-list"),
    path("consultation-services/<uuid:public_id>/", ServiceDetailView.as_view(), name="service-detail"),
    path("consultations/", ConsultationListStartView.as_view(), name="case-list-start"),
    path("consultations/<uuid:public_id>/", ConsultationDetailView.as_view(), name="case-detail"),
    path("consultations/<uuid:public_id>/questionnaire/", ConsultationQuestionnaireView.as_view(), name="questionnaire"),
    path("consultations/<uuid:public_id>/answers/", ConsultationAnswersView.as_view(), name="answers"),
    path("consultations/<uuid:public_id>/submit/", ConsultationSubmitView.as_view(), name="submit"),
    path("consultations/<uuid:public_id>/photos/", ConsultationPhotosView.as_view(), name="photos"),
    path("consultations/<uuid:public_id>/photos/submit/", ConsultationPhotosSubmitView.as_view(), name="photos-submit"),
    path(
        "consultations/<uuid:public_id>/photos/<uuid:photo_id>/",
        ConsultationPhotoDetailView.as_view(),
        name="photo-detail",
    ),
    path("private-files/photos/<uuid:photo_id>/", PrivatePhotoContentView.as_view(), name="photo-content"),
    path("staff/consultations/", StaffConsultationListView.as_view(), name="staff-case-list"),
    path("staff/consultations/<uuid:public_id>/", StaffConsultationDetailView.as_view(), name="staff-case-detail"),
    path("availability/slots/", AvailableSlotsView.as_view(), name="available-slots"),
    path("appointments/", AppointmentListCreateView.as_view(), name="appointment-list-create"),
    path("appointments/<uuid:public_id>/", AppointmentDetailView.as_view(), name="appointment-detail"),
    path("appointments/<uuid:public_id>/reschedule/", AppointmentRescheduleView.as_view(), name="appointment-reschedule"),
    path("appointments/<uuid:public_id>/cancel/", AppointmentCancelView.as_view(), name="appointment-cancel"),
    path("staff/availability/weekly/", StaffWeeklyAvailabilityView.as_view(), name="staff-availability-weekly"),
    path(
        "staff/availability/exceptions/",
        StaffAvailabilityExceptionListCreateView.as_view(),
        name="staff-availability-exceptions",
    ),
    path(
        "staff/availability/exceptions/<uuid:public_id>/",
        StaffAvailabilityExceptionDetailView.as_view(),
        name="staff-availability-exception-detail",
    ),
    path("staff/appointments/", StaffAppointmentListView.as_view(), name="staff-appointment-list"),
]
