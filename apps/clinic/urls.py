"""
clinic/urls.py
All URLs for BUK Smart Clinic System — Receptionist + Nurse roles.
"""

from django.urls import path
from . import views

app_name = "clinic"

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # ── Receptionist pages ────────────────────────────────────────────────────
    path("reception/search/", views.search_view, name="search"),
    path("reception/register/", views.register_view, name="register"),
    path("reception/profile/", views.profile_view, name="profile"),
    # Receptionist HTMX partials
    path("reception/patient-search/", views.patient_search_htmx, name="patient_search"),
    path(
        "reception/checkin/<int:patient_id>/",
        views.checkin_patient,
        name="checkin_patient",
    ),
    path("reception/emergency/", views.emergency_mode, name="emergency_mode"),
    path("reception/queue-stats/", views.queue_stats_partial, name="queue_stats"),
    path(
        "reception/recent-checkins/",
        views.recent_checkins_partial,
        name="recent_checkins",
    ),
    # ── Nurse pages ───────────────────────────────────────────────────────────
    path("nurse/", views.nurse_queue_view, name="nurse_queue"),
    path("nurse/profile/", views.nurse_profile_view, name="nurse_profile"),
    path(
        "nurse/vitals/<int:encounter_id>/",
        views.capture_vitals_view,
        name="capture_vitals",
    ),
    # Nurse HTMX partials
    path("nurse/live-queue/", views.nurse_live_queue_partial, name="nurse_live_queue"),
    path("nurse/emergency/", views.emergency_mode, name="nurse_emergency"),
]
