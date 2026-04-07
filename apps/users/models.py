from django.db import models
from django.contrib.auth.models import AbstractUser,BaseUserManager
# Create your models here.

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)
    
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        RECEPTIONIST = "RECEPTIONIST", "Receptionist"
        NURSE = "NURSE", "Nurse"
        DOCTOR = "DOCTOR", "Doctor"
        LAB_TECH = "LAB_TECH", "Lab Technician"
        PHARMACIST = "PHARMACIST", "Pharmacist"

    # Remove username, use email as unique identifier
    username = None 
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    staff_id = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["staff_id", "first_name", "last_name"]

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
    
