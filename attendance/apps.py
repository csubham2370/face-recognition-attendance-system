from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    name = "attendance"

    def ready(self):
        from . import signals  # noqa: F401
