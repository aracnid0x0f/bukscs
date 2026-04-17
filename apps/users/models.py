"""
apps/users/models.py
Custom User model with role-based access for BUK Smart Clinic System.
All six roles: Admin, Receptionist, Nurse, Doctor, Lab Technician, Pharmacist.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        RECEPTIONIST = "RECEPTIONIST", "Receptionist"
        NURSE = "NURSE", "Nurse"
        DOCTOR = "DOCTOR", "Doctor"
        LAB_TECH = "LAB_TECH", "Lab Technician"
        PHARMACIST = "PHARMACIST", "Pharmacist"

    # Use email as the login identifier instead of username
    username = None
    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.RECEPTIONIST
    )
    staff_id = models.CharField(max_length=20, unique=True)

    # Profile fields used in templates / topbar
    phone_number = models.CharField(max_length=20, blank=True)
    profile_photo = models.ImageField(upload_to="staff/photos/", null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["staff_id", "first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    # ── Convenience helpers used in views / templates ──────────────
    @property
    def is_receptionist(self):
        return self.role == self.Role.RECEPTIONIST

    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def is_nurse(self):
        return self.role == self.Role.NURSE

    @property
    def is_pharmacist(self):
        return self.role == self.Role.PHARMACIST

    @property
    def is_lab_tech(self):
        return self.role == self.Role.LAB_TECH

    @property
    def is_admin_staff(self):
        return self.role == self.Role.ADMIN
