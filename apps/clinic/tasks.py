from celery import shared_task
import time

from .models  import Encounter, Patient

@shared_task
def notify_department_queue(encounter_id, department):
    try:
        encounter = Encounter.objects.get(id=encounter_id)
        patient_name = f"{encounter.patient.last_name}, {encounter.patient.first_name}"
        
        # In a real scenario, this would trigger a WebSocket push
        print(f"--- RABBITMQ NOTIFICATION ---")
        print(f"TARGET: {department}")
        print(f"PATIENT: {patient_name}")
        print(f"CLINIC ID: {encounter.patient.clinic_code}")
        print(f"-----------------------------")
        
        return True
    except Encounter.DoesNotExist:
        return False

@shared_task
def generate_visit_summary(encounter_id):
    """
    Heavy task: Generates a PDF summary of the visit once closed.
    """
    time.sleep(5) # Simulate heavy PDF generation
    print(f"PDF Generated for Encounter {encounter_id}")