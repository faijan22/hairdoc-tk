from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "HairDoc TK Administration"
admin.site.site_title = "HairDoc TK Admin"
admin.site.index_title = "Operations"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls")),
]

