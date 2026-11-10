from django.urls import path
from . import views

app_name = "birthdays"

urlpatterns = [
    path("calendar/", views.calendar_api, name="calendar"),
    path("day/", views.day_birthdays_api, name="day_birthdays"),
    path("card/", views.birthday_card_api, name="birthday_card"),
    path("logs/", views.birthday_email_logs_api, name="logs"),
]
