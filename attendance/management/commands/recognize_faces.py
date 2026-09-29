from django.core.management.base import (
    BaseCommand
)

from attendance.ml.recognize import (
    run_face_recognition
)


class Command(BaseCommand):

    help = "Run live student face recognition"


    def handle(self, *args, **options):

        self.stdout.write(
            "Starting face recognition..."
        )

        try:

            run_face_recognition()

        except Exception as error:

            self.stdout.write(
                self.style.ERROR(
                    f"Recognition error: {error}"
                )
            )