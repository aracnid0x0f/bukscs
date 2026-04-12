"""
clinic/views.py
All views scoped to the receptionist. Every action stays within the dashboard.
"""
import json
import re
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import Encounter, Patient
from .forms import (
    PatientRegistrationForm, SIFUploadForm,
    ReceptionistProfileForm, PasswordChangeForm,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _require_receptionist(request):
    """Raise PermissionDenied if the logged-in user is not a receptionist."""
    if not request.user.is_authenticated:
        return False
    role = getattr(request.user, "role", "")
    return role in ("RECEPTIONIST", "ADMIN")


def _queue_stats():
    today = timezone.now().date()
    return {
        "waiting_nurse":  Encounter.objects.filter(status=Encounter.Status.RECEPTION).count(),
        "with_doctor":    Encounter.objects.filter(status=Encounter.Status.CONSULTATION).count(),
        "in_lab":         Encounter.objects.filter(status=Encounter.Status.LABORATORY).count(),
        "at_pharmacy":    Encounter.objects.filter(status=Encounter.Status.PHARMACY).count(),
        "closed_today":   Encounter.objects.filter(status=Encounter.Status.CLOSED, closed_at__date=today).count(),
        "emergency":      Encounter.objects.filter(status=Encounter.Status.EMERGENCY).count(),
    }


def _recent_encounters():
    today = timezone.now().date()
    return (
        Encounter.objects
        .select_related("patient")
        .filter(created_at__date=today)
        .exclude(status=Encounter.Status.CLOSED)
        .order_by("-priority", "created_at")[:15]
    )


def _extract_sif_fields(document_file):
    """
    Attempt lightweight text extraction from a SIF document.
    Works on plain-text-layer PDFs. Returns a dict of prefill values.
    We use pdfplumber if available, otherwise return empty dict.
    """
    prefill = {}
    name = document_file.name.lower()

    try:
        if name.endswith(".pdf"):
            import pdfplumber
            document_file.seek(0)
            with pdfplumber.open(document_file) as pdf:
                text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        else:
            # For images, OCR would be needed — return empty for now
            return prefill

        # BUK reg number pattern  e.g. BUK/21/MED/0042 or SCI/19/COM/0001
        m = re.search(r"[A-Z]{2,4}/\d{2}/[A-Z]{2,5}/\d{3,5}", text, re.I)
        if m:
            prefill["reg_number"] = m.group(0).upper()

        # Phone  +234XXXXXXXXXX or 0XXXXXXXXXX
        m = re.search(r"(\+?234[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{4}|0\d{10})", text)
        if m:
            prefill["phone_number"] = re.sub(r"[\s-]", "", m.group(0))

        # Email
        m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        if m:
            prefill["email"] = m.group(0)

        # Faculty / Department — look for common label patterns
        for label, key in [("Faculty", "faculty"), ("Department", "department")]:
            m = re.search(rf"{label}[:\s]+([A-Za-z &/]+)", text, re.I)
            if m:
                prefill[key] = m.group(1).strip()[:100]

        # Level
        m = re.search(r"\b(100|200|300|400|500|600)\s*[Ll]evel", text)
        if m:
            prefill["level"] = int(m.group(1))

    except Exception:
        pass

    return prefill


# ─── Auth ─────────────────────────────────────────────────────────────────────

def login_view(request):
    error = None
    if request.method == "POST":
        staff_id = request.POST.get("staff_id", "").strip()
        password = request.POST.get("password", "")

        # USERNAME_FIELD is email, so we look up the user by staff_id first
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()
        try:
            user_obj = UserModel.objects.get(staff_id=staff_id)
            user = authenticate(request, username=user_obj.email, password=password)
        except UserModel.DoesNotExist:
            user = None

        if user and user.is_active:
            login(request, user)
            return redirect("clinic:search")
        error = "Invalid staff ID or password. Please try again."
    return render(request, "login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("clinic:login")


# ─── Dashboard shell guard ─────────────────────────────────────────────────────

def _ctx(request):
    """Base context injected into every receptionist view."""
    return {
        "queue_stats":     _queue_stats(),
        "recent_encounters": _recent_encounters(),
        "today": timezone.now().date(),
    }


# ─── Search / Check-in ────────────────────────────────────────────────────────

@login_required(login_url="clinic:login")
def search_view(request):
    if not _require_receptionist(request):
        raise PermissionDenied
    ctx = _ctx(request)
    ctx["active_nav"] = "search"
    return render(request, "clinic/search.html", ctx)


@login_required(login_url="clinic:login")
@login_required(login_url="clinic:login")
@require_GET
def patient_search_htmx(request):
    """HTMX partial: search patient by reg_number, clinic_code, or full name."""
    q = request.GET.get("q", "").strip()

    if len(q) < 2:
        return render(request, "clinic/partials/search_hint.html", {"query": q})

    from django.db.models import Q
    patient = Patient.objects.filter(
        Q(reg_number__icontains=q) |
        Q(clinic_code__iexact=q) |
        Q(first_name__icontains=q) |
        Q(last_name__icontains=q)
    ).first()

    if patient:
        active_encounter = patient.encounters.exclude(status=Encounter.Status.CLOSED).first()
        return render(request, "clinic/partials/patient_card.html", {
            "patient": patient,
            "active_encounter": active_encounter,
        })

    return render(request, "clinic/partials/patient_not_found.html", {"query": q})


@login_required(login_url="clinic:login")
@require_POST
def checkin_patient(request, patient_id):
    """HTMX POST: create an Encounter ticket and push to nurse queue."""
    if not _require_receptionist(request):
        raise PermissionDenied

    patient = get_object_or_404(Patient, pk=patient_id)

    if patient.has_active_encounter:
        active = patient.encounters.exclude(status=Encounter.Status.CLOSED).first()
        return render(request, "clinic/partials/patient_card.html", {
            "patient": patient,
            "active_encounter": active,
            "checkin_error": "Patient already has an open ticket.",
        })

    priority = int(request.POST.get("priority", Encounter.Priority.NORMAL))
    encounter = Encounter.objects.create(
        patient=patient,
        status=Encounter.Status.RECEPTION,
        priority=priority,
        checked_in_by=request.user,
    )

    try:
        from .tasks import notify_department_queue
        notify_department_queue.delay(str(encounter.visit_id), "NURSE")
    except Exception:
        pass

    response = render(request, "clinic/partials/checkin_success.html", {
        "patient": patient,
        "encounter": encounter,
        "today": timezone.now().date(),
    })
    response["HX-Trigger"] = json.dumps({"refreshQueue": True, "refreshRecent": True})
    return response


# ─── Register Patient ─────────────────────────────────────────────────────────

@login_required(login_url="clinic:login")
def register_view(request):
    """
    Two-step registration page:
      GET  → empty form + SIF upload
      POST with action=upload_sif → save file, extract fields, return pre-filled form
      POST with action=submit_registration → validate & save patient
    """
    if not _require_receptionist(request):
        raise PermissionDenied

    ctx = _ctx(request)
    ctx["active_nav"] = "register"
    ctx["sif_form"] = SIFUploadForm()
    ctx["reg_form"] = PatientRegistrationForm()
    ctx["prefill"] = {}

    if request.method == "POST":
        action = request.POST.get("action", "")

        # ── Step 1: SIF upload + extraction ──
        if action == "upload_sif":
            sif_form = SIFUploadForm(request.POST, request.FILES)
            if sif_form.is_valid():
                doc = request.FILES["sif_document"]
                prefill = _extract_sif_fields(doc)
                # Store file temporarily in session for step 2
                # We'll re-attach it when saving
                ctx["sif_form"] = sif_form
                ctx["reg_form"] = PatientRegistrationForm(initial=prefill)
                ctx["prefill"] = prefill
                ctx["sif_uploaded"] = True
                # Store filename in session for display
                request.session["pending_sif_name"] = doc.name
                # Save file to a temp location using Django's default storage
                from django.core.files.storage import default_storage
                tmp_path = default_storage.save(f"patients/sif/tmp_{doc.name}", doc)
                request.session["pending_sif_path"] = tmp_path
            else:
                ctx["sif_form"] = sif_form
            return render(request, "clinic/register.html", ctx)

        # ── Step 2: Full registration submission ──
        if action == "submit_registration":
            reg_form = PatientRegistrationForm(request.POST, request.FILES)
            if reg_form.is_valid():
                patient = reg_form.save(commit=False)
                # Attach the previously uploaded SIF document
                sif_path = request.session.pop("pending_sif_path", None)
                if sif_path:
                    patient.sif_document = sif_path
                patient.save()
                # Clean session
                request.session.pop("pending_sif_name", None)
                ctx["reg_form"] = PatientRegistrationForm()
                ctx["sif_form"] = SIFUploadForm()
                ctx["registered_patient"] = patient
            else:
                ctx["reg_form"] = reg_form
                ctx["sif_uploaded"] = bool(request.session.get("pending_sif_path"))
                ctx["sif_form"] = SIFUploadForm()
            return render(request, "clinic/register.html", ctx)

    return render(request, "clinic/register.html", ctx)


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required(login_url="clinic:login")
def profile_view(request):
    if not _require_receptionist(request):
        raise PermissionDenied

    user = request.user
    profile_form  = ReceptionistProfileForm(instance=user)
    password_form = PasswordChangeForm()
    profile_saved  = False
    password_saved = False
    password_error = None

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "update_profile":
            profile_form = ReceptionistProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                profile_saved = True

        elif action == "change_password":
            password_form = PasswordChangeForm(request.POST)
            if password_form.is_valid():
                if user.check_password(password_form.cleaned_data["current_password"]):
                    user.set_password(password_form.cleaned_data["new_password"])
                    user.save()
                    # Re-authenticate to keep session alive
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, user)
                    password_saved = True
                    password_form = PasswordChangeForm()
                else:
                    password_error = "Current password is incorrect."

    ctx = _ctx(request)
    ctx.update({
        "active_nav":     "profile",
        "profile_form":   profile_form,
        "password_form":  password_form,
        "profile_saved":  profile_saved,
        "password_saved": password_saved,
        "password_error": password_error,
        # Performance stats
        "checkins_today": Encounter.objects.filter(
            checked_in_by=user,
            created_at__date=timezone.now().date()
        ).count(),
        "checkins_total": Encounter.objects.filter(checked_in_by=user).count(),
    })
    return render(request, "clinic/profile.html", ctx)


# ─── Emergency Mode ───────────────────────────────────────────────────────────

@login_required(login_url="clinic:login")
@require_POST
def emergency_mode(request):
    """Notify the system of a clinic emergency via RabbitMQ/Celery."""
    if not _require_receptionist(request):
        raise PermissionDenied
    try:
        from .tasks import broadcast_emergency
        broadcast_emergency.delay(
            triggered_by=request.user.get_full_name() or request.user.username,
            note=request.POST.get("note", "Emergency flagged at reception."),
        )
        return JsonResponse({"status": "ok", "message": "Emergency alert broadcast."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


# ─── HTMX Polling Partials ────────────────────────────────────────────────────

@login_required(login_url="clinic:login")
@require_GET
def queue_stats_partial(request):
    return render(request, "clinic/partials/queue_stats.html", {"queue_stats": _queue_stats()})


@login_required(login_url="clinic:login")
@require_GET
def recent_checkins_partial(request):
    return render(request, "clinic/partials/recent_checkins.html", {
        "recent_encounters": _recent_encounters(),
    })


# TODO: 1. create a STAFF ID generator