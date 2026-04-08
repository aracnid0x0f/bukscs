from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required
def role_dispatch(request):
    """
    Redirects users to their specific dashboard based on their assigned role.
    """
    role = request.user.role

    if role == 'ADMIN':
        return redirect('admin_dashboard')
    elif role == 'RECEPTIONIST':
        return redirect('receptionist_dashboard')
    elif role == 'DOCTOR':
        return redirect('doctor_dashboard')
    elif role == 'NURSE':
        return redirect('nurse_dashboard') # Or nurse_dashboard
    elif role == 'LAB_SCIENTIST':
        return redirect('lab_dashboard')
    
    # Default fallback
    return redirect('receptionist_dashboard')