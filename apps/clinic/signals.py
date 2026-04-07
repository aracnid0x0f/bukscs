from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Encounter
from .tasks import notify_department_queue

@receiver(post_save, sender=Encounter)
def handle_status_change(sender, instance, created, **kwargs):
    if created:
        # New ticket created at Reception -> Notify Nurses
        notify_department_queue.delay(instance.id, "NURSING")
    
    # If the status was just updated to PHARMACY
    elif instance.status == 'PHARMACY':
        notify_department_queue.delay(instance.id, "PHARMACY")