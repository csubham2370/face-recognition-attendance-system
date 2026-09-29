from django.core.management.base import (
    BaseCommand
)

from attendance.ml.train_model import (
    train_face_model
)


class Command(BaseCommand):

    help = "Train CNN face recognition model"


    def handle(self, *args, **options):

        self.stdout.write(
            "Starting CNN training..."
        )


        try:

            result = train_face_model()


            self.stdout.write(
                self.style.SUCCESS(
                    "CNN training completed."
                )
            )


            self.stdout.write(
                f"Classes: "
                f"{result['class_names']}"
            )

            self.stdout.write(
                f"Training accuracy: {result['accuracy']:.2%}\n"
                f"Validation accuracy: {result['validation_accuracy']:.2%}"
            )


        except Exception as error:

            self.stdout.write(
                self.style.ERROR(
                    f"Training failed: {error}"
                )
            )
