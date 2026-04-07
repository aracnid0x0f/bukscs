from django.apps import AppConfig


class ClinicConfig(AppConfig):
    name = 'apps.clinic'

    def ready(self):
        import apps.clinic.signals
