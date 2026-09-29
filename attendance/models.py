
from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class Student(models.Model):

    student_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to="student_photos/",blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_id} - {self.name}"


class Attendance(models.Model):

    student = models.ForeignKey(Student, on_delete=models.CASCADE,related_name="attendance_records")
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20,default="Present")
    confidence = models.FloatField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        constraints = [models.UniqueConstraint(fields=["student","date"],
                      name="unique_student_attendance_per_day")]

    def __str__(self):

        return (f"{self.student.student_id} " f"- {self.date} " f"- {self.status}")




class AdminUser(models.Model):

    username = models.CharField(max_length=100,unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reset_token = models.CharField(max_length=255,null=True,blank=True)
    reset_token_created_at = models.DateTimeField(null=True,blank=True)


    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):

        return check_password(raw_password,self.password)

  



    def __str__(self):

        return self.username


class AttendanceControl(models.Model):
    is_open = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        AdminUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_control_changes",
    )

    def __str__(self):
        return "Attendance open" if self.is_open else "Attendance closed"
