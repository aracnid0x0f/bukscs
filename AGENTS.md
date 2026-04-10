# Agent Coding Guidelines for BUKSCS

## Project Overview

- **Type**: Django web application (Django 6.0.4+) with Python 3.12+
- **Async Tasks**: Celery with RabbitMQ broker, django-celery-results backend
- **Frontend**: TailwindCSS 4.x
- **Database**: SQLite3 (default), uses django.db.backends.sqlite3

---

## Build / Run Commands

### Python/Django

```bash
# Install dependencies
pip install -r requirements.txt  # if exists, else pip install -e .

# Run Django development server
python manage.py runserver

# Apply migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Run a single test (by path)
python manage.py test apps.clinic.tests.PatientTestCase

# Run all tests
python manage.py test

# Collect static files
python manage.py collectstatic
```

### Celery

```bash
# Start Celery worker
celery -A core worker -l info

# Start Celery beat (scheduler)
celery -A core beat -l info
```

### Frontend (TailwindCSS)

```bash
# Install Node dependencies
npm install

# Build CSS (watch mode)
npm run dev
```

---

## Code Style Guidelines

### Git Configuration

Always ensure `.gitignore` includes Python cache patterns:
```
__pycache__/
*.pyc
*.pyo
*.pyd
```
If files are already tracked, clear the index with: `git rm -r --cached .`

### Imports

Order imports within each file:
1. Standard library (`from pathlib import Path`)
2. Third-party packages (`from django.db import models`)
3. Local application imports (`from apps.users.models import User`)

Use explicit relative imports for app modules:
```python
from apps.users.models import User  # NOT: from ..users.models import User
```

### Django Models

- Use `TextChoices` for enum-like fields:
```python
class Encounter(models.Model):
    class Status(models.TextChoices):
        RECEPTION = "RECEPTION", "Awaiting Vitals"
```
- Always define `__str__` methods on models
- Use `related_name` on ForeignKey fields
- Define `Meta` classes for `ordering` and other model-level options
- Use `auto_now_add`/`auto_now` for timestamps

### Views

- Use Django's shortcuts: `get_object_or_404`, `render`, `redirect`
- Always handle POST requests with proper CSRF consideration (Django handles via template tag)
- Use `messages` framework for user feedback
- Filter querysets based on user permissions where applicable

### Naming Conventions

- **Python**: `snake_case` for functions, variables; `PascalCase` for classes
- **URL names**: `snake_case` (e.g., `url_name='receptionist_dashboard'`)
- **Templates**: lowercase with underscores (`clinic/receptionist_dash.html`)
- **Database fields**: `snake_case` (`clinic_code`, `reg_number`)

### Error Handling

- Use Django's `get_object_or_404()` for single object retrieval
- Catch specific exceptions (`Patient.DoesNotExist`) when needed
- Use `messages.error()` / `messages.warning()` for user-facing errors
- Let Django handle 404/500 pages via custom views if needed

#### UI/Styling for Status

- Use conditional CSS classes for emergency vs routine cases:
  - `bg-tertiary` for urgent/emergency cases
  - `bg-primary` for routine cases
- Highlight the "Active" patient in sidebar via `visit_id` query parameter

### Templates

- Store in `templates/<app_name>/<view_name>.html`
- Use TailwindCSS classes for styling
- Load required template tags: `{% load static %}`

#### Django Template Language (DTL) Patterns

- Use context variables: `{{ user.get_full_name }}`, `{{ active_visit.patient }}`
- Use `{% for %}` loops for lists/queues
- Use `{% if %}` for conditional rendering
- Always include `{% csrf_token %}` in forms
- Use `{% url %}` for dynamic action URLs

#### Frontend Stack

- TailwindCSS 4.x (can use CDN for prototyping)
- Material Symbols Outlined for icons
- Bento Grid layout for dashboard interfaces

---

## Testing Guidelines

- Place tests in `<app>/tests.py` or `<app>/tests/` package
- Extend `django.test.TestCase` for integration tests
- Use Django's test client for view testing
- Run single test: `python manage.py test apps.clinic.tests.SomeTestCase.test_method`

---

## File Structure

```
bukscs/
├── apps/
│   ├── clinic/      # Patient, Encounter, Prescription models
│   ├── laboratory/ # Lab-related models/views
│   ├── pharmacy/   # Medicine, Dispensation models
│   └── users/      # Custom User model
├── core/
│   ├── settings.py # Django configuration
│   ├── urls.py     # Root URL configuration
│   └── celery.py   # Celery app setup
├── templates/       # Shared templates
├── static/         # CSS, JS, images
└── manage.py
```

---

## Key Models

- **Patient**: University student medical records (reg_number as unique identifier)
- **Encounter**: Visit/ticket tracking with status flow (RECEPTION → TRIAGE → CONSULTATION → LAB → PHARMACY → CLOSED)
- **Prescription**: Doctor prescriptions linked to encounters

---

## Common Workflows

1. **Register Patient**: Receptionist creates Patient record → generates clinic_code
2. **Create Encounter**: Receptionist creates ticket with RECEPTION status
3. **Triage**: Nurse records vitals, moves to TRIAGE status
4. **Consultation**: Doctor reviews, adds diagnosis, routes to LAB or PHARMACY
5. **Dispensation**: Pharmacy fills prescription, marks DISPENSED

---

## Notes

- Custom user model: `AUTH_USER_MODEL = 'users.User'`
- Celery broker: RabbitMQ on `localhost:5672`
- Timezone: Africa/Lagos (BUK local time)
