from django.urls import path

from .views import ClientCasePlanListView, ClientPlanDetailView, ClientPlanListView, StaffCasePlanListCreateView, StaffPlanDetailView, StaffPlanPublishView

app_name = "coaching"

urlpatterns = [
    path("plans/", ClientPlanListView.as_view(), name="client-plan-list"),
    path("plans/<uuid:public_id>/", ClientPlanDetailView.as_view(), name="client-plan-detail"),
    path("consultations/<uuid:case_id>/plans/", ClientCasePlanListView.as_view(), name="client-case-plan-list"),
    path("staff/consultations/<uuid:case_id>/plans/", StaffCasePlanListCreateView.as_view(), name="staff-case-plan-list"),
    path("staff/plans/<uuid:public_id>/", StaffPlanDetailView.as_view(), name="staff-plan-detail"),
    path("staff/plans/<uuid:public_id>/publish/", StaffPlanPublishView.as_view(), name="staff-plan-publish"),
]
