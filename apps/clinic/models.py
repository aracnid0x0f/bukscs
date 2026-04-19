"""
clinic/models.py
Core clinical models: Patient, Encounter (ticket), Prescription.
"""
import uuid
import random
from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_clinic_number():
    for _ in range(30):
        number = str(random.randint(100000, 999999)) # TODO: check for the starting boundary for the cc generation and change this
        if not Patient.objects.filter(clinic_code=number).exists():
            return number
    raise RuntimeError("Could not generate a unique clinic code.")


class Patient(models.Model):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female")]

    # Identification
    first_name    = models.CharField(max_length=255)
    middle_name   = models.CharField(max_length=255, blank=True)
    last_name     = models.CharField(max_length=255)
    reg_number    = models.CharField(max_length=30, unique=True)
    gender        = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    clinic_code   = models.CharField(max_length=6, blank=True, unique=True)
    phone_number  = models.CharField(max_length=20, blank=True)
    email         = models.EmailField(blank=True)

    # University
    faculty    = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    level      = models.IntegerField(null=True, blank=True)
    address    = models.TextField(blank=True)

    # Medical baseline
    blood_group     = models.CharField(max_length=5, blank=True)
    genotype        = models.CharField(max_length=5, blank=True)
    allergies       = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)

    # Emergency contact
    next_of_kin_name  = models.CharField(max_length=255, blank=True)
    next_of_kin_phone = models.CharField(max_length=20, blank=True)

    # File uploads
    photo        = models.ImageField(upload_to="patients/photos/", null=True, blank=True)
    sif_document = models.FileField(
        upload_to="patients/sif/",
        null=True, blank=True,
        help_text="Student Information Form — PDF or image"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def save(self, *args, **kwargs):
        if not self.clinic_code:
            self.clinic_code = generate_clinic_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reg_number} — {self.last_name}, {self.first_name}"

    @property
    def full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)

    @property
    def display_name(self):
        """LASTNAME, Firstname Middlename format."""
        rest = self.first_name
        if self.middle_name:
            rest += f" {self.middle_name}"
        return f"{self.last_name.upper()}, {rest}"

    @property
    def initials(self):
        return f"{self.first_name[:1]}{self.last_name[:1]}".upper()

    @property
    def has_active_encounter(self):
        return self.encounters.exclude(status=Encounter.Status.CLOSED).exists()

    @property
    def last_visit(self):
        return self.encounters.order_by("-created_at").first()

    @property
    def visit_count(self):
        return self.encounters.count()


class Encounter(models.Model):

    class Status(models.TextChoices):
        RECEPTION    = "RECEPTION",    "Awaiting Vitals"
        TRIAGE       = "TRIAGE",       "Awaiting Consultation"
        CONSULTATION = "CONSULTATION", "With Doctor"
        LABORATORY   = "LAB",          "In Laboratory"
        PHARMACY     = "PHARMACY",     "Awaiting Medication"
        CLOSED       = "CLOSED",       "Completed"
        EMERGENCY    = "EMERGENCY",    "Emergency"

    class Priority(models.IntegerChoices):
        NORMAL    = 1, "Normal"
        URGENT    = 2, "Urgent"
        EMERGENCY = 3, "Emergency"

    patient  = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="encounters")
    visit_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status   = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEPTION)
    priority = models.IntegerField(choices=Priority.choices, default=Priority.NORMAL)

    # Triage (Nurse fills)
    temperature    = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    weight         = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, blank=True, null=True)
    heart_rate     = models.IntegerField(null=True, blank=True)
    spo2           = models.IntegerField(null=True, blank=True, help_text="Blood oxygen saturation %")
    triage_notes   = models.TextField(blank=True)

    # Consultation (Doctor fills)
    chief_complaint = models.TextField(blank=True)
    clinical_notes  = models.TextField(blank=True)
    diagnosis       = models.TextField(blank=True)

    doctor_assigned = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="doctor_encounters",
        limit_choices_to={"role": "DOCTOR"},
    )
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="checkins_done",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    closed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-priority", "created_at"]

    def __str__(self):
        return f"{self.ticket_number} — {self.patient.reg_number} [{self.get_status_display()}]"

    @property
    def ticket_number(self):
        n = str(self.visit_id.int)[-4:]
        return f"#TK-{n}"

    def close(self):
        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=["status", "closed_at"])


class Prescription(models.Model):
    class Status(models.TextChoices):
        PENDING      = "PENDING",      "Pending"
        DISPENSED    = "DISPENSED",    "Dispensed"
    encounter       = models.ForeignKey(Encounter, on_delete=models.PROTECT, related_name="prescriptions")
    doctor          = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="prescriptions_issued",
        limit_choices_to={"role": "DOCTOR"},
    )
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    issued_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.doctor.get_full_name()} → {self.encounter.patient.reg_number}"

class PrescriptionItem(models.Model):
    class Status(models.TextChoices):
        PENDING      = "PENDING",      "Pending"
        DISPENSED    = "DISPENSED",    "Dispensed"
        OUT_OF_STOCK = "OUT_OF_STOCK", "Out of Stock"

    name        = models.CharField(max_length=255)
    dosage       = models.CharField(max_length=100)
    frequency    = models.CharField(max_length=100)
    duration     = models.CharField(max_length=50)
    instructions = models.TextField(max_length=500, blank=True)
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="items")
    dispensed_at  = models.DateTimeField(null=True, blank=True)
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    def __str__(self):
        return f"{self.name} for {self.prescription.encounter.patient.reg_number}"