from django.urls import path
from . import views


urlpatterns = [
    # Receptionist
    path("reception/", views.receptionist_dashboard, name="receptionist_dashboard"),
    path(
        "reception/check-in/<int:patient_id>/",
        views.create_encounter,
        name="check_in_patient",
    ),
    path("register/", views.register_student, name="register_student"),
    # Nurse (Triage)
    path("triage/", views.triage_list, name="triage_list"),
    path("triage/<uuid:visit_id>/", views.triage_detail, name="triage_detail"),
    path("emergency-alert/", views.emergency_protocol, name="emergency_protocol"),
    # Doctor (Consultation)
    path("consultation/", views.doctor_list, name="doctor_list"),
    path(
        "consultation/<uuid:visit_id>/",
        views.consultation_detail,
        name="consultation_detail",
    ),
]
