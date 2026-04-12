"""
clinic/urls.py
All URLs scoped to the receptionist dashboard.
"""

from django.urls import path
from . import views

app_name = "clinic"

urlpatterns = [
    # Auth
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Main pages
    path("reception/search/", views.search_view, name="search"),
    path("reception/register/", views.register_view, name="register"),
    path("reception/profile/", views.profile_view, name="profile"),
    # HTMX search partial
    path("reception/patient-search/", views.patient_search_htmx, name="patient_search"),
    path(
        "reception/checkin/<int:patient_id>/",
        views.checkin_patient,
        name="checkin_patient",
    ),
    # Emergency
    path("reception/emergency/", views.emergency_mode, name="emergency_mode"),
    # Polling partials
    path("reception/queue-stats/", views.queue_stats_partial, name="queue_stats"),
    path(
        "reception/recent-checkins/",
        views.recent_checkins_partial,
        name="recent_checkins",
    ),
]
