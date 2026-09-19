from django.urls import path

from .views import HealthView, HomeView

app_name = "core"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("home/", HomeView.as_view(), name="home"),
]
