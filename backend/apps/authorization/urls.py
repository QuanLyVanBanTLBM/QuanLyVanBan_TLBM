from django.urls import path

from . import views

app_name = "authorization"

urlpatterns = [
    path("roles/", views.group_list_create_view, name="role-list-create"),
    path("roles/<int:pk>/", views.group_detail_view, name="role-detail"),
    path("roles/<int:pk>/permissions/", views.group_permissions_view, name="role-permissions"),
    path("permissions/", views.permission_list_view, name="permission-list"),
    path("auth/me/permissions/", views.my_permissions_view, name="my-permissions"),
]
