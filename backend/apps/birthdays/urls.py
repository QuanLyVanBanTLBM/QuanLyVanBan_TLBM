from django.urls import path
from . import draft_ai, manual_views, views

app_name = "birthdays"

urlpatterns = [
    path("calendar/", views.calendar_api, name="calendar"),
    path("day/", views.day_birthdays_api, name="day_birthdays"),
    path("card/", views.birthday_card_api, name="birthday_card"),
    path("logs/", views.birthday_email_logs_api, name="logs"),
    path("logs/resend/", manual_views.resend_api, name="resend_email"),
    path("logs/<int:log_id>/retry/", manual_views.retry_api, name="retry_email"),
    path("recipients/", manual_views.recipients_api, name="manual_recipients"),
    path("templates/", manual_views.templates_api, name="email_templates"),
    path("templates/draft/", draft_ai.draft_api, name="ai_email_draft"),
    path("manual/preview/", manual_views.preview_api, name="manual_preview"),
    path("manual/send/", manual_views.send_api, name="manual_send"),
]
