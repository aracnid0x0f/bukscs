from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from .models import Encounter

# Create your views here.

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

def consultation_detail(request, visit_id):
    encounter = get_object_or_404(Encounter, visit_id=visit_id)
    
    if request.method == "POST":
        encounter.chief_complaint = request.POST.get('complaint')
        encounter.diagnosis = request.POST.get('diagnosis')
        # Logic to decide if they go to Lab or Pharmacy
        if request.POST.get('action') == 'to_lab':
            encounter.status = 'LAB'
        else:
            encounter.status = 'PHARMACY'
        
        encounter.save()
        return redirect('doctor_list')

    return render(request, 'clinic/doctor_detail.html', {'encounter': encounter})