import uuid

from django.db import models

from core import settings as settings
from apps.users.models import User

# Create your models here.
class Patient(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]

    # Identification
    first_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255)
    reg_number = models.CharField(max_length=50, unique=True) # Primary Key for BUK
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    clinic_code = models.CharField(max_length=20, blank=True) # e.g. "000-000"
    
    # University Specifics
    faculty = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    level = models.IntegerField(null=True, blank=True) # e.g., 100, 200...
    
    # Medical Essentials (The "Big File" baseline)
    blood_group = models.CharField(max_length=5, blank=True)
    genotype = models.CharField(max_length=5, blank=True)
    allergies = models.TextField(blank=True, help_text="List all known allergies")
    medical_history = models.TextField(blank=True, help_text="Chronic conditions, past surgeries, etc.")
    
    # Emergency Contact
    next_of_kin_name = models.CharField(max_length=255, blank=True)
    next_of_kin_phone = models.CharField(max_length=15, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.reg_number} - {self.full_name}"


class Encounter(models.Model):
    class Status(models.TextChoices):
        RECEPTION = "RECEPTION", "Awaiting Vitals"
        TRIAGE = "TRIAGE", "Awaiting Consultation"
        CONSULTATION = "CONSULTATION", "With Doctor"
        LABORATORY = "LAB", "In Laboratory"
        PHARMACY = "PHARMACY", "Awaiting Medication"
        CLOSED = "CLOSED", "Completed"

    # Linking the Ticket to the File
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="encounters")
    
    # Unique Ticket ID for this visit
    visit_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # The Flow Logic
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEPTION)
    priority = models.IntegerField(default=1, help_text="1: Normal, 2: Urgent, 3: Emergency")
    
    # Data points filled as the ticket moves
    # Triage Data (Nurse)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    
    # Consultation Data (Doctor)
    chief_complaint = models.TextField(blank=True)
    clinical_notes = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    
    # Assignment Tracking
    doctor_assigned = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="doctor_encounters"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-priority', 'created_at']

    def __str__(self):
        return f"Encounter {self.visit_id} for {self.patient.reg_number}"
    
class Prescription(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Dispensation"
        DISPENSED = "DISPENSED", "Dispensed"
        OUT_OF_STOCK = "OUT_OF_STOCK", "Out of Stock"

    encounter = models.ForeignKey("Encounter", on_delete=models.CASCADE, related_name="prescriptions")
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'DOCTOR'})
    
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100) # e.g., "500mg"
    frequency = models.CharField(max_length=100) # e.g., "2x Daily"
    duration = models.CharField(max_length=50) # e.g., "5 Days"
    
    instructions = models.TextField(blank=True) # e.g., "Take after meals"
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    issued_at = models.DateTimeField(auto_now_add=True)
    dispensed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.medication_name} for {self.encounter.patient.full_name}"