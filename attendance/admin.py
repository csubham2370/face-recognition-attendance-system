# Register your models here.
from django.contrib import admin
from .models import Student, Attendance, AttendanceControl


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    list_display = ("student_id", "name","email","created_at",)
    search_fields = ("student_id","name","email",)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = ("student","date","time","status","confidence",)
    list_filter = ("date","status",)
    search_fields = ("student__student_id","student__name",)


@admin.register(AttendanceControl)
class AttendanceControlAdmin(admin.ModelAdmin):
    list_display = ("is_open", "updated_at", "updated_by")
