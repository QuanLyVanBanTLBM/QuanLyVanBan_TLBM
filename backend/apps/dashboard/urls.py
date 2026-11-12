from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # Tổng hợp số liệu Dashboard
    path("overview/", views.overview_view, name="overview"),
]
