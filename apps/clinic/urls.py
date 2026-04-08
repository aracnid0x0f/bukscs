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
    path("triage/", views.nurse_dashboard, name="nurse_dashboard"),
    path("triage/submit/<uuid:visit_id>/", views.submit_vitals, name="submit_vitals"),
    path("emergency-alert/", views.emergency_protocol, name="emergency_protocol"),

    # Doctor (Consultation)
    path("consultation/", views.doctor_list, name="doctor_list"),
    path(
        "consultation/<uuid:visit_id>/",
        views.consultation_detail,
        name="consultation_detail",
    ),
]
