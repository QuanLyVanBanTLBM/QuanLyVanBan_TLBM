from django.urls import include, path
from rest_framework.routers import SimpleRouter

from work import views

app_name = "work"

router = SimpleRouter()
router.register("tasks", views.TaskViewSet, basename="task")
router.register("attachments", views.AttachmentViewSet, basename="attachment")
router.register("employees", views.EmployeeViewSet, basename="employee")

# Được include tại config/urls.py với tiền tố "api/work/".
urlpatterns = [
    path("me/", views.MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
