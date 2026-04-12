"""
clinic/forms.py
"""

from django import forms
from django.contrib.auth import get_user_model
from .models import Patient

User = get_user_model()

LEVEL_CHOICES = [
    ("", "— Select —"),
    (100, "100L"),
    (200, "200L"),
    (300, "300L"),
    (400, "400L"),
    (500, "500L"),
    (600, "600L"),
]

BLOOD_GROUP_CHOICES = [("", "— Unknown —")] + [
    (x, x) for x in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
]
GENOTYPE_CHOICES = [("", "— Unknown —")] + [
    (x, x) for x in ["AA", "AS", "SS", "AC", "SC"]
]


class SIFUploadForm(forms.Form):
    """Step 1: Upload the SIF document (PDF or image)."""

    sif_document = forms.FileField(
        label="SIF Document",
        help_text="Upload the Student Information Form (PDF or JPG/PNG)",
        widget=forms.FileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png"}),
    )


class PatientRegistrationForm(forms.ModelForm):
    """Step 2: Bio-data entry (pre-filled from AI extraction if available)."""

    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    level = forms.ChoiceField(choices=LEVEL_CHOICES, required=False)
    blood_group = forms.ChoiceField(choices=BLOOD_GROUP_CHOICES, required=False)
    genotype = forms.ChoiceField(choices=GENOTYPE_CHOICES, required=False)

    class Meta:
        model = Patient
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "reg_number",
            "gender",
            "date_of_birth",
            "phone_number",
            "email",
            "faculty",
            "department",
            "level",
            "address",
            "blood_group",
            "genotype",
            "allergies",
            "medical_history",
            "next_of_kin_name",
            "next_of_kin_phone",
            "photo",
        ]
        widgets = {
            "allergies": forms.Textarea(attrs={"rows": 2}),
            "medical_history": forms.Textarea(attrs={"rows": 2}),
            "address": forms.Textarea(attrs={"rows": 2}),
            "photo": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def clean_reg_number(self):
        return self.cleaned_data["reg_number"].strip().upper()

    def clean_level(self):
        val = self.cleaned_data.get("level")
        return int(val) if val else None


class ReceptionistProfileForm(forms.ModelForm):
    """Edit profile details."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new_password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("New passwords do not match.")
        return cleaned
