from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0005_student_unique_id_case_insensitive"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="student",
            name="unique_student_id_case_insensitive",
        ),
    ]
