"""
clinic/tasks.py
Celery async tasks for the clinic app.
"""

from celery import shared_task


@shared_task(bind=True, max_retries=3)
def notify_department_queue(self, visit_id: str, department: str):
    """
    Push an encounter ticket to the appropriate department queue via RabbitMQ.
    The department consumers (Nurse, Doctor, etc.) will pick this up.
    """
    try:
        from .models import Encounter

        encounter = Encounter.objects.select_related("patient").get(visit_id=visit_id)
        # TODO: publish to RabbitMQ exchange keyed by department
        # For now, log the event
        print(
            f"[QUEUE] Ticket {encounter.ticket_number} → {department} | "
            f"Patient: {encounter.patient.reg_number} | Priority: {encounter.priority}"
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)


@shared_task
def broadcast_emergency(triggered_by: str, note: str):
    """
    Broadcast an emergency alert to all active staff sessions.
    Publishes to a fanout exchange so every logged-in role sees it.
    """
    print(f"[EMERGENCY] Triggered by {triggered_by}: {note}")
    # TODO: publish to RabbitMQ fanout exchange 'clinic.emergency'
