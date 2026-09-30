from django.urls import path

from . import views

app_name = "authorization"

urlpatterns = [
    path("groups/", views.group_list_create_view, name="group-list-create"),
    path("groups/<int:pk>/", views.group_detail_view, name="group-detail"),
    path("permissions/", views.permission_list_view, name="permission-list"),
]
