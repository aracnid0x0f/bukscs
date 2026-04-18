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
from django.db.models import Q


from .models import Encounter, Patient
from .forms import (
    PatientRegistrationForm,
    SIFUploadForm,
    ReceptionistProfileForm,
    PasswordChangeForm,
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
        "waiting_nurse": Encounter.objects.filter(
            status=Encounter.Status.RECEPTION
        ).count(),
        "with_doctor": Encounter.objects.filter(
            status=Encounter.Status.CONSULTATION
        ).count(),
        "in_lab": Encounter.objects.filter(status=Encounter.Status.LABORATORY).count(),
        "at_pharmacy": Encounter.objects.filter(
            status=Encounter.Status.PHARMACY
        ).count(),
        "closed_today": Encounter.objects.filter(
            status=Encounter.Status.CLOSED, closed_at__date=today
        ).count(),
        "emergency": Encounter.objects.filter(
            status=Encounter.Status.EMERGENCY
        ).count(),
    }


def _recent_encounters():
    today = timezone.now().date()
    return (
        Encounter.objects.select_related("patient")
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
            if user.role in ("NURSE",):
                login(request, user)
                return redirect("clinic:nurse_queue")
            else:
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
        "queue_stats": _queue_stats(),
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

    patient = Patient.objects.filter(
        Q(reg_number__icontains=q)
        | Q(clinic_code__iexact=q)
        | Q(first_name__icontains=q)
        | Q(last_name__icontains=q)
    ).first()

    if patient:
        active_encounter = patient.encounters.exclude(
            status=Encounter.Status.CLOSED
        ).first()
        return render(
            request,
            "clinic/partials/patient_card.html",
            {
                "patient": patient,
                "active_encounter": active_encounter,
            },
        )

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
        return render(
            request,
            "clinic/partials/patient_card.html",
            {
                "patient": patient,
                "active_encounter": active,
                "checkin_error": "Patient already has an open ticket.",
            },
        )

    priority = int(request.POST.get("priority", Encounter.Priority.NORMAL))
    encounter = Encounter.objects.create(
        patient=patient,
        status=Encounter.Status.RECEPTION,
        priority=priority,
        checked_in_by=request.user,
    )

    response = render(
        request,
        "clinic/partials/checkin_success.html",
        {
            "patient": patient,
            "encounter": encounter,
            "today": timezone.now().date(),
        },
    )
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
    profile_form = ReceptionistProfileForm(instance=user)
    password_form = PasswordChangeForm()
    profile_saved = False
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
    ctx.update(
        {
            "active_nav": "profile",
            "profile_form": profile_form,
            "password_form": password_form,
            "profile_saved": profile_saved,
            "password_saved": password_saved,
            "password_error": password_error,
            # Performance stats
            "checkins_today": Encounter.objects.filter(
                checked_in_by=user, created_at__date=timezone.now().date()
            ).count(),
            "checkins_total": Encounter.objects.filter(checked_in_by=user).count(),
        }
    )
    return render(request, "clinic/profile.html", ctx)


# ─── Emergency Mode ───────────────────────────────────────────────────────────


@login_required(login_url="clinic:login")
@require_POST
def emergency_mode(request):
    """Notify the system of a clinic emergency via RabbitMQ/Celery."""
    if not _require_receptionist(request):
        raise PermissionDenied


# ─── HTMX Polling Partials ────────────────────────────────────────────────────


@login_required(login_url="clinic:login")
@require_GET
def queue_stats_partial(request):
    return render(
        request, "clinic/partials/queue_stats.html", {"queue_stats": _queue_stats()}
    )


@login_required(login_url="clinic:login")
@require_GET
def recent_checkins_partial(request):
    return render(
        request,
        "clinic/partials/recent_checkins.html",
        {
            "recent_encounters": _recent_encounters(),
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
# NURSE VIEWS
# ══════════════════════════════════════════════════════════════════════════════


def _require_nurse(request):
    """Return True only for Nurse or Admin roles."""
    if not request.user.is_authenticated:
        return False
    return getattr(request.user, "role", "") in ("NURSE", "ADMIN")

def _nurse_queue_stats():
    """Stats for the nurse right-pane."""
    today = timezone.now().date()
    return {
        "today": Encounter.objects.filter(created_at__date=today).count(),
        "critical": Encounter.objects.filter(priority=Encounter.Priority.EMERGENCY)
        .exclude(status=Encounter.Status.CLOSED)
        .count(),
        "waiting": Encounter.objects.filter(status=Encounter.Status.RECEPTION).count(),
    }


def _nurse_live_queue():
    """All open encounters ordered by priority DESC then arrival ASC."""
    return (
        Encounter.objects.select_related("patient")
        .exclude(status__in=[Encounter.Status.CLOSED])
        .order_by("-priority", "created_at")[:20]
    )


def _nurse_ctx(request):
    return {
        "queue_stats": _nurse_queue_stats(),
        "live_queue": _nurse_live_queue(),
        "today": timezone.now().date(),
    }

# ── Patient Queue (Awaiting Vitals) ───────────────────────────────────────────


@login_required(login_url="clinic:login")
def nurse_queue_view(request):
    if not _require_nurse(request):
        raise PermissionDenied
    ctx = _nurse_ctx(request)
    ctx["active_nav"] = "queue"
    ctx["awaiting"] = (
        Encounter.objects.select_related("patient")
        .filter(status=Encounter.Status.RECEPTION)
        .order_by("-priority", "created_at")
    )
    return render(request, "nurse/queue.html", ctx)


# ── Capture Vitals ────────────────────────────────────────────────────────────


@login_required(login_url="clinic:login")
def     capture_vitals_view(request, encounter_id):
    if not _require_nurse(request):
        raise PermissionDenied

    encounter = get_object_or_404(
        Encounter.objects.select_related("patient"),
        pk=encounter_id,
        status=Encounter.Status.RECEPTION,
    )

    if request.method == "POST":
        action = request.POST.get("action", "submit")

        # Save vitals from the Encounter model fields
        encounter.temperature = request.POST.get("temperature") or None
        encounter.heart_rate = request.POST.get("heart_rate") or None
        encounter.blood_pressure = request.POST.get("blood_pressure", "").strip()
        encounter.weight = request.POST.get("weight") or None
        encounter.spo2 = request.POST.get("spo2") or None
        encounter.triage_notes = request.POST.get("triage_notes", "").strip()

        if action == "discard":
            # Don't save — just redirect back to queue
            return redirect("clinic:nurse_queue")

        # Save vitals and advance status to TRIAGE (→ awaiting doctor)
        encounter.status = Encounter.Status.TRIAGE
        encounter.save()

        return redirect("clinic:nurse_queue")

    ctx = _nurse_ctx(request)
    ctx["active_nav"] = "queue"
    ctx["encounter"] = encounter
    return render(request, "nurse/capture_vitals.html", ctx)


# ── Nurse Profile ─────────────────────────────────────────────────────────────


@login_required(login_url="clinic:login")
def nurse_profile_view(request):
    if not _require_nurse(request):
        raise PermissionDenied

    user = request.user
    profile_saved = False
    password_saved = False
    password_error = None

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "update_profile":
            user.first_name = request.POST.get("first_name", user.first_name).strip()
            user.last_name = request.POST.get("last_name", user.last_name).strip()
            user.email = request.POST.get("email", user.email).strip()
            user.phone_number = request.POST.get(
                "phone_number", user.phone_number
            ).strip()
            user.save(
                update_fields=["first_name", "last_name", "email", "phone_number"]
            )
            profile_saved = True

        elif action == "change_password":
            cur = request.POST.get("current_password", "")
            new = request.POST.get("new_password", "")
            conf = request.POST.get("confirm_password", "")
            if not user.check_password(cur):
                password_error = "Current password is incorrect."
            elif new != conf:
                password_error = "New passwords do not match."
            elif len(new) < 8:
                password_error = "Password must be at least 8 characters."
            else:
                user.set_password(new)
                user.save()
                from django.contrib.auth import update_session_auth_hash

                update_session_auth_hash(request, user)
                password_saved = True

    today = timezone.now().date()
    ctx = _nurse_ctx(request)
    ctx.update(
        {
            "active_nav": "profile",
            "profile_saved": profile_saved,
            "password_saved": password_saved,
            "password_error": password_error,
            # Performance stats
            "vitals_today": Encounter.objects.filter(
                status__in=[
                    Encounter.Status.TRIAGE,
                    Encounter.Status.CONSULTATION,
                    Encounter.Status.LABORATORY,
                    Encounter.Status.PHARMACY,
                    Encounter.Status.CLOSED,
                ],
                created_at__date=today,
            ).count(),
            "vitals_total": Encounter.objects.exclude(
                status=Encounter.Status.RECEPTION
            ).count(),
        }
    )
    return render(request, "nurse/profile.html", ctx)


# ── Nurse HTMX Partials ───────────────────────────────────────────────────────


@login_required(login_url="clinic:login")
@require_GET
def nurse_live_queue_partial(request):
    return render(
        request,
        "nurse/partials/live_queue.html",
        {
            "live_queue": _nurse_live_queue(),
            "queue_stats": _nurse_queue_stats(),
        },
    )


# -- Doctor Views -------------------------------------------------------------

def _doctor_queue_stats():
    """Stats for the doctor right-pane."""
    today = timezone.now().date()
    return {
        "today": Encounter.objects.filter(created_at__date=today).count(),
        "critical": Encounter.objects.filter(priority=Encounter.Priority.EMERGENCY)
        .exclude(status=Encounter.Status.CLOSED)
        .count(),
        "waiting": Encounter.objects.filter(status=Encounter.Status.TRIAGE).count(),
    }

def _doctor_live_queue():
    """All open encounters ordered by priority DESC then arrival ASC."""
    return (
        Encounter.objects.select_related("patient")
        .exclude(status__in=[Encounter.Status.CLOSED])
        .order_by("-priority", "created_at")[:20]
    )

def _doctor_ctx(request):
    return {
        "queue_stats": _doctor_queue_stats(),
        "live_queue": _doctor_live_queue(),
        "today": timezone.now().date(),
    }

def _require_doctor(request):
    """Return True only for Doctor or Admin roles."""
    if not request.user.is_authenticated:
        return False
    return getattr(request.user, "role", "") in ("DOCTOR", "ADMIN")

@login_required(login_url="clinic:login")
def doctor_queue_view(request):
    if not _require_doctor(request):
        raise PermissionDenied
    ctx = _doctor_ctx(request)
    ctx["active_nav"] = "queue"
    ctx["awaiting"] = (
        Encounter.objects.select_related("patient")
        .filter(status__in=[Encounter.Status.TRIAGE, Encounter.Status.EMERGENCY])
        .order_by("-priority", "created_at")
    )

    return render(request, "doctor/queue.html", ctx)

@login_required(login_url="clinic:login")
def doctor_consultation_view(request, encounter_id):
    if not _require_doctor(request):
        raise PermissionDenied
    
    encounter = get_object_or_404(
        Encounter.objects.select_related("patient"),
        pk=encounter_id,
        status__in=[Encounter.Status.TRIAGE, Encounter.Status.EMERGENCY]   # which statuses can the doctor open?
    )

    if request.method == "POST":
        # 1. save the four fields from request.POST
        encounter.chief_complaint = request.POST.get("chief_complaint", "").strip()
        encounter.diagnosis = request.POST.get("diagnosis", "").strip()
        encounter.clinical_notes = request.POST.get("clinical_notes", "").strip()
        # 2. assign doctor_assigned
        encounter.doctor_assigned = request.user # i dont know how to o this
        # 3. read the routing decision
        # 4. set the correct status
        if request.POST.get("action") == "send_to_lab":
            encounter.status = Encounter.Status.LABORATORY
        elif request.POST.get("action") == "send_to_pharmacy":
            encounter.status = Encounter.Status.PHARMACY
        # 5. save the encounter
        encounter.save()
        # 6. redirect back to queue
        return redirect("clinic:doctor_queue")

    # GET
    ctx = _doctor_ctx(request)
    ctx["encounter"] = encounter
    ctx["active_nav"] = "queue"
    return render(request, "doctor/consultation.html", ctx)
    

@login_required(login_url="clinic:login")
def doctor_profile_view(request):
    if not _require_doctor(request):
        raise PermissionDenied()

    user = request.user
    profile_saved = False
    password_saved = False
    password_error = None

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "update_profile":
            user.first_name = request.POST.get("first_name", user.first_name).strip()
            user.last_name = request.POST.get("last_name", user.last_name).strip()
            user.email = request.POST.get("email", user.email).strip()
            user.phone_number = request.POST.get(
                "phone_number", user.phone_number
            ).strip()
            user.save(
                update_fields=["first_name", "last_name", "email", "phone_number"]
            )
            profile_saved = True

        elif action == "change_password":
            cur = request.POST.get("current_password", "")
            new = request.POST.get("new_password", "")
            conf = request.POST.get("confirm_password", "")
            if not user.check_password(cur):
                password_error = "Current password is incorrect."
            elif new != conf:
                password_error = "New passwords do not match."
            elif len(new) < 8:
                password_error = "Password must be at least 8 characters."
            else:
                user.set_password(new)
                user.save()
                from django.contrib.auth import update_session_auth_hash

                update_session_auth_hash(request, user)
                password_saved = True

        today = timezone.now().date()
        ctx = _doctor_ctx(request)
        ctx.update({
                "active_nav": "profile",
                "profile_saved": profile_saved,
                "password_saved": password_saved,
                "password_error": password_error,
                "visits_today": Encounter.objects.filter(doctor_assigned=user, created_at__date=today).count(),
                "visits_total": Encounter.objects.filter(doctor_assigned=user).count(),
        })

        return render(request, "doctor/profile.html", ctx)


@login_required(login_url="clinic:login")
def doctor_patient_search_view(request):
    if not _require_doctor(request):
        raise PermissionDenied()
    
    q = request.GET.get("q", "").strip()
    patients = []

    patients = Patient.objects.filter(
        Q(reg_number__icontains=q) |
        Q(clinic_code__iexact=q) |
        Q(first_name__icontains=q) |
        Q(last_name__icontains=q)
    ).order_by("last_name")

    ctx = _doctor_ctx(request)
    ctx.update({
        "patients": patients,
        "query": q,
        "active_nav": "patient",

    })

    return render(request, "doctor/patient_search.html", ctx)


@login_required(login_url="clinic:login")
def doctor_patient_details_view(request, patient_id):
    if not _require_doctor(request):
        raise PermissionDenied()

    patient = get_object_or_404(Patient, pk=patient_id)
    encounters = patient.encounters.order_by("-created_at")
    ctx = _doctor_ctx(request)
    ctx.update({
        "active_nav": "patient",
        "patient": patient,
        "encounters": encounters,
    })

    return render(request, "doctor/patient_details.html", ctx)