from django.shortcuts import render, get_object_or_404, redirect
from apps.clinic.models import Encounter, Prescription
from .models import Medicine, StockTransaction
from django.db import transaction

def pharmacy_dashboard(request):
    # Get all tickets waiting at the pharmacy
    queue = Encounter.objects.filter(status='PHARMACY').order_by('created_at')
    return render(request, 'pharmacy/dashboard.html', {'queue': queue})

def dispense_medication(request, visit_id):
    encounter = get_object_or_404(Encounter, visit_id=visit_id)
    prescriptions = encounter.prescriptions.all()

    if request.method == "POST":
        # Use an atomic transaction so if one drug fails, none are deducted
        
        with transaction.atomic():
            for p in prescriptions:
                # Deduct from inventory logic
                medicine = Medicine.objects.get(name=p.medication_name)
                if medicine.quantity_in_stock < p.quantity:
                    messages.error(request, f"{medicine.name} does not have enough stock to fulfill the prescription.")
                    return redirect('pharmacy_dashboard')
                
                if medicine.quantity_in_stock >= 1: # Basic check
                    medicine.quantity_in_stock -= 1 
                    medicine.save()
                    
                    # Log the transaction
                    StockTransaction.objects.create(
                        medicine=medicine,
                        quantity=-1,
                        transaction_type='OUT',
                        note=f"Dispensed for Ticket {encounter.visit_id}"
                    )
            
            # Close the encounter
            encounter.status = 'CLOSED'
            encounter.save()
            
        return redirect('pharmacy_dashboard')

    return render(request, 'pharmacy/dispense_detail.html', {
        'encounter': encounter,
        'prescriptions': prescriptions
    })