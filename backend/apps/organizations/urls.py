from django.urls import path
from . import views

app_name = "organizations"

urlpatterns = [
    # API Khối / Khu vực (Cấp 1)
    path("regions/", views.region_list_create_view, name="region-list-create"),
    path("regions/<int:pk>/", views.region_detail_view, name="region-detail"),

    # API Đơn vị / Phòng ban (Cấp 2)
    path("units/", views.unit_list_create_view, name="unit-list-create"),
    path("units/<int:pk>/", views.unit_detail_view, name="unit-detail"),
    path("units/export/", views.unit_export_excel_view, name="unit-export-excel"),
]
