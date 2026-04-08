from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone

from .models import Encounter, Patient
from apps.pharmacy.models import Medicine
from .tasks import notify_department_queue

# Create your views here.

## Receptionist views
def receptionist_dashboard(request):
    query = request.GET.get('search', '')
    patient = None
    
    if query:
        # Search by Reg Number or Clinic Number
        patient = Patient.objects.filter(
            reg_number__iexact=query
        ).first() or Patient.objects.filter(
            clinic_code=query
        ).first()

        if not patient:
            messages.info(request, f"No record found for '{query}'. Please register the student.")

    return render(request, 'clinic/receptionist_dash.html', {
        'patient': patient,
        'query': query
    })

def register_student(request):
    if request.method == "POST":
        # Capture the 3 names as requested
        new_patient = Patient.objects.create(
            first_name=request.POST.get('first_name'),
            middle_name=request.POST.get('middle_name'),
            last_name=request.POST.get('last_name'),
            reg_number=request.POST.get('reg_number'),
            faculty=request.POST.get('faculty'),
            department=request.POST.get('department'),
            gender=request.POST.get('gender'),
            date_of_birth=request.POST.get('dob'),
        )
        messages.success(request, f"Registered! Clinic ID: {new_patient.clinic_code}")
        return redirect('receptionist_dashboard')
    
    return render(request, 'clinic/register_student.html')

def create_encounter(request, patient_id):
    if request.method == "POST":
        patient = get_object_or_404(Patient, id=patient_id)
        
        # Check if they already have an active ticket
        active_ticket = Encounter.objects.filter(patient=patient, status__exclude='CLOSED').exists()
        
        if active_ticket:
            messages.error(request, "This student already has an active session.")
        else:
            # Create the Ticket
            Encounter.objects.create(
                patient=patient,
                status='RECEPTION'
            )
            messages.success(request, f"Ticket created for {patient.full_name}. Sent to Nursing.")
            
        return redirect('receptionist_dashboard')


def consultation_detail(request, visit_id):
    encounter = get_object_or_404(Encounter, visit_id=visit_id)
    medicines = Medicine.objects.all() # To populate the prescription section

    if request.method == "POST":
        encounter.chief_complaint = request.POST.get('complaint')
        encounter.clinical_notes = request.POST.get('notes')
        encounter.diagnosis = request.POST.get('diagnosis')
        
        # Determine next destination
        action = request.POST.get('next_step')
        if action == 'lab':
            encounter.status = 'LAB'
        else:
            encounter.status = 'PHARMACY'
            
        encounter.save()
        messages.success(request, f"Consultation for {encounter.patient.full_name} completed.")
        return redirect('doctor_list')

    return render(request, 'clinic/doctor_detail.html', {
        'encounter': encounter,
        'medicines': medicines
    })

def check_in_patient(request, patient_id):
    patient = Patient.objects.get(id=patient_id)

    # Create the Encounter (The "Ticket")
    encounter = Encounter.objects.create(
        patient=patient,
        status='RECEPTION', # Start of the flow
        priority=request.POST.get('priority', 1)
    )

    notify_department_queue(encounter_id=encounter.id, department='NURSING')

    messages.success(request, f"Ticket generated for {patient.last_name}. Proceed to Nursing Triage.")
    return redirect('receptionist_dashboard')

def emergency_protocol(request):
    """
    Handles immediate emergency flagging.
    In a production EMR, this would trigger a WebSocket or push notification
    to the Nurse/Doctor dashboards.
    """
    # 1. Create a placeholder or anonymous visit if no patient is selected
    # or redirect to a quick-registration form.
    # For now, let's trigger a system-wide alert or redirect to a high-priority form.

    if request.method == "POST":
        # Logic to handle a specific emergency patient if ID is provided
        patient_id = request.POST.get("patient_id")

        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id)
                Encounter.objects.create(
                    patient=patient,
                    status="EMERGENCY",  # Ensure this status exists in your Model choices
                    check_in_time=timezone.now(),
                    priority_level=3,  # 1=Normal, 2=Urgent, 3=Emergency
                )
                messages.error(
                    request,
                    f"EMERGENCY TICKET CREATED for {patient.last_name} {patient.first_name}. Patient moved to top of Nurse queue.",
                )

            except Patient.DoesNotExist:
                messages.warning(
                    request,
                    "Patient record not found. Proceeding with Anonymous Emergency Protocol.",
                )

        # If no patient ID, we log a "General Emergency" to notify staff
        else:
            messages.error(
                request,
                "GENERAL EMERGENCY ALERT INITIATED. Medical team has been notified.",
            )

    return redirect("receptionist_dashboard")

## Nurse views
def triage_list(request):
    # Only show students who have been checked in by reception but haven't seen a nurse
    queue = Encounter.objects.filter(status='RECEPTION').order_by('-priority', 'created_at')
    return render(request, 'clinic/triage_list.html', {'queue': queue})

def triage_detail(request, visit_id):
    encounter = get_object_or_404(Encounter, visit_id=visit_id)
    
    if request.method == "POST":
        encounter.temperature = request.POST.get('temp')
        encounter.blood_pressure = request.POST.get('bp')
        encounter.weight = request.POST.get('weight')
        # Move the ticket to the next desk
        encounter.status = 'TRIAGE' 
        encounter.save()
        messages.success(request, f"Vitals recorded for {encounter.patient.full_name}. Sent to Doctor.")
        return redirect('triage_list')

    return render(request, 'clinic/triage_detail.html', {'encounter': encounter})

## Doctor views
def doctor_list(request):
    # Queue for patients ready for consultation
    queue = Encounter.objects.filter(status='TRIAGE').order_by('-priority', 'created_at')
    return render(request, 'clinic/doctor_list.html', {'queue': queue})
