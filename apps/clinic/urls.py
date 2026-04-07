from django.urls import path
from . import views

urlpatterns = [
    # Receptionist
    path('reception/', views.reception_dashboard, name='reception_dashboard'),
    path('reception/check-in/<int:patient_id>/', views.create_encounter, name='create_encounter'),
    
    # Nurse (Triage)
    path('triage/', views.triage_list, name='triage_list'),
    path('triage/<uuid:visit_id>/', views.triage_detail, name='triage_detail'),
    
    # Doctor (Consultation)
    path('consultation/', views.doctor_list, name='doctor_list'),
    path('consultation/<uuid:visit_id>/', views.consultation_detail, name='consultation_detail'),
]