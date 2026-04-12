from django.contrib import admin
from .models import Patient, Encounter, Prescription


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "reg_number",
        "clinic_code",
        "full_name",
        "faculty",
        "department",
        "level",
        "created_at",
    )
    search_fields = ("reg_number", "clinic_code", "first_name", "last_name")
    list_filter = ("faculty", "gender")
    readonly_fields = ("clinic_code", "created_at", "updated_at")


class PrescriptionInline(admin.TabularInline):
    model = Prescription
    extra = 0
    fields = ("medication_name", "dosage", "frequency", "duration", "status")


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "patient",
        "status",
        "priority",
        "doctor_assigned",
        "created_at",
    )
    list_filter = ("status", "priority")
    search_fields = ("patient__reg_number", "patient__first_name", "patient__last_name")
    readonly_fields = ("visit_id", "ticket_number", "created_at")
    inlines = [PrescriptionInline]


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("medication_name", "encounter", "doctor", "status", "issued_at")
    list_filter = ("status",)
