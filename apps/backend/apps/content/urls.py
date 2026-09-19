from django.urls import path

from .views import ContentItemDetailView, ContentItemListView

app_name = "content"

urlpatterns = [
    path("", ContentItemListView.as_view(), name="list"),
    path("<uuid:public_id>/", ContentItemDetailView.as_view(), name="detail"),
]

