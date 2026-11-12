from django.urls import path

from . import views_position as views

app_name = "positions"

urlpatterns = [
    path("", views.position_list_create_view, name="position-list-create"),
    path("import-template/", views.position_import_template_view, name="position-import-template"),
    path("import/", views.position_import_view, name="position-import"),
    path("<int:pk>/", views.position_detail_view, name="position-detail"),
]
