from django.contrib import admin

from .models import Patient, Encounter, Prescription

# Register your models here.

class EncounterInline(admin.TabularInline):
    model = Encounter
    extra = 0  # Don't show empty extra slots
    readonly_fields = ['visit_id', 'created_at']

class PrescriptionInline(admin.TabularInline):
    model = Prescription
    extra = 0

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['reg_number', 'first_name', 'middle_name', 'last_name', 'faculty', 'level']
    search_fields = ['reg_number', 'first_name', 'middle_name', 'last_name']
    inlines = [EncounterInline]

@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ['visit_id', 'patient', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority']
    inlines = [PrescriptionInline]