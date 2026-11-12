from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("accounts.urls", namespace="accounts")),
    path("api/records/", include("records.urls", namespace="records")),
]
