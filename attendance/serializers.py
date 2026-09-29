import re

from rest_framework import serializers

from .models import AdminUser, Attendance, Student


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["id", "date", "time", "status", "confidence"]
        read_only_fields = fields


class StudentSerializer(serializers.ModelSerializer):
    face_capture_url = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ["id", "student_id", "name", "email", "photo", "created_at", "face_capture_url"]
        read_only_fields = ["id", "created_at", "face_capture_url"]

    def validate_student_id(self, value):
        student_id = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", student_id):
            raise serializers.ValidationError(
                "Use only letters, numbers, hyphens, and underscores in the student ID."
            )

        duplicate = Student.objects.filter(student_id=student_id)
        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError("A student with this ID already exists.")
        return student_id

    def get_face_capture_url(self, student):
        request = self.context.get("request")
        path = f"/students/{student.id}/capture/"
        return request.build_absolute_uri(path) if request else path


class StudentDetailSerializer(StudentSerializer):
    attendance_records = AttendanceSerializer(many=True, read_only=True)

    class Meta(StudentSerializer.Meta):
        fields = StudentSerializer.Meta.fields + ["attendance_records"]


class AdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model = AdminUser
        fields = ["id", "username", "email", "password", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_username(self, value):
        duplicate = AdminUser.objects.filter(username__iexact=value.strip())
        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError("An admin with this username already exists.")
        return value.strip()

    def validate_email(self, value):
        duplicate = AdminUser.objects.filter(email__iexact=value.strip())
        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError("An admin with this email already exists.")
        return value.strip()

    def validate(self, attrs):
        request = self.context.get("request")
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Password is required when creating an admin."})
        if (
            self.instance is not None
            and request is not None
            and self.instance.id == getattr(request.user, "id", None)
            and attrs.get("is_active") is False
        ):
            raise serializers.ValidationError({"is_active": "You cannot deactivate your own signed-in account."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        admin = AdminUser(**validated_data)
        admin.set_password(password)
        admin.save()
        return admin

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
