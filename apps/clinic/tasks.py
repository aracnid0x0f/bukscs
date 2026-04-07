from celery import shared_task
import time

@shared_task
def notify_department_queue(encounter_id, department):
    """
    Simulates sending a real-time notification to a specific department.
    In a full production app, this would trigger a WebSocket (Django Channels).
    """
    # Logic to alert the destination desk
    print(f"ALARM: New Patient for {department}. Ticket ID: {encounter_id}")
    return True

@shared_task
def generate_visit_summary(encounter_id):
    """
    Heavy task: Generates a PDF summary of the visit once closed.
    """
    time.sleep(5) # Simulate heavy PDF generation
    print(f"PDF Generated for Encounter {encounter_id}")