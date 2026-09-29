from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0004_adminuser_reset_token_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="student",
            constraint=models.UniqueConstraint(
                Lower("student_id"),
                name="unique_student_id_case_insensitive",
            ),
        ),
    ]
