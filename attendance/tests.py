import json
from smtplib import SMTPException
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import cv2
import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .jwt_utils import create_access_token
from .models import AdminUser, AttendanceControl, Student


class ForgotPasswordTests(TestCase):
    def setUp(self):
        self.admin = AdminUser(username="admin", email="Admin@Example.com")
        self.admin.set_password("old-password")
        self.admin.save()
        self.url = reverse("attendance:forgot_password")

    @patch("attendance.views.send_mail", return_value=1)
    def test_sends_reset_email_and_saves_token(self, send_mail_mock):
        response = self.client.post(self.url, {"email": "admin@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.admin.refresh_from_db()
        self.assertIsNotNone(self.admin.reset_token)
        self.assertIsNotNone(self.admin.reset_token_created_at)
        self.assertEqual(send_mail_mock.call_args.kwargs["recipient_list"], [self.admin.email])

    @patch("attendance.views.send_mail", side_effect=SMTPException("authentication failed"))
    def test_returns_clear_error_and_removes_token_when_email_fails(self, _send_mail_mock):
        response = self.client.post(self.url, {"email": self.admin.email})

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["success"])
        self.admin.refresh_from_db()
        self.assertIsNone(self.admin.reset_token)
        self.assertIsNone(self.admin.reset_token_created_at)


class StudentCrudTests(TestCase):
    def setUp(self):
        self.admin = AdminUser(username="admin", email="admin@example.com")
        self.admin.set_password("admin-password")
        self.admin.save()
        self.client.cookies["access_token"] = create_access_token(self.admin)

    def test_create_and_view_student(self):
        response = self.client.post(
            reverse("attendance:register_student"),
            {"student_id": "STU100", "name": "Test Student", "email": "student@example.com"},
        )

        student = Student.objects.get(student_id="STU100")
        self.assertRedirects(response, reverse("attendance:capture_face", args=[student.id]))

        response = self.client.get(reverse("attendance:student_detail", args=[student.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Student")
        self.assertContains(response, "student@example.com")

    def test_face_capture_page_and_upload_validation(self):
        student = Student.objects.create(
            student_id="STU-CAPTURE", name="Camera Student", email="camera@example.com"
        )
        page_response = self.client.get(reverse("attendance:capture_face", args=[student.id]))
        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, "collect exactly 30 detected photos")

        upload_response = self.client.post(reverse("attendance:capture_face_image", args=[student.id]))
        self.assertEqual(upload_response.status_code, 400)
        self.assertEqual(upload_response.json()["message"], "Camera image was not received.")

    @patch("attendance.views.cv2.CascadeClassifier", create=True)
    def test_face_capture_saves_exactly_thirty_training_photos(self, detector_class):
        student = Student.objects.create(
            student_id="STU30", name="Thirty Photos", email="thirty@example.com"
        )
        detector_class.return_value.detectMultiScale.return_value = np.array([[20, 20, 120, 120]])
        checkerboard = np.indices((180, 180)).sum(axis=0) % 2 * 255
        sharp_image = np.repeat(checkerboard[:, :, np.newaxis], 3, axis=2).astype(np.uint8)
        success, encoded_image = cv2.imencode(".jpg", sharp_image)
        self.assertTrue(success)

        with TemporaryDirectory() as temporary_directory, self.settings(BASE_DIR=Path(temporary_directory)):
            capture_url = reverse("attendance:capture_face_image", args=[student.id])
            response = None
            for image_number in range(30):
                image = SimpleUploadedFile("camera.jpg", encoded_image.tobytes(), content_type="image/jpeg")
                data = {"image": image}
                if image_number == 0:
                    data["reset"] = "true"
                response = self.client.post(capture_url, data)
                self.assertEqual(response.status_code, 200)

            self.assertEqual(response.json()["captured_count"], 30)
            self.assertTrue(response.json()["complete"])
            saved_images = list((Path(temporary_directory) / "dataset" / "STU30").glob("face_*.jpg"))
            self.assertEqual(len(saved_images), 30)

    def test_update_student(self):
        student = Student.objects.create(
            student_id="STU101", name="Old Name", email="old@example.com"
        )

        response = self.client.post(
            reverse("attendance:update_student", args=[student.id]),
            {"student_id": "STU101", "name": "New Name", "email": "new@example.com"},
        )

        self.assertRedirects(response, reverse("attendance:student_detail", args=[student.id]))
        student.refresh_from_db()
        self.assertEqual(student.name, "New Name")
        self.assertEqual(student.email, "new@example.com")

    def test_delete_requires_confirmation_post(self):
        student = Student.objects.create(
            student_id="STU102", name="Delete Me", email="delete@example.com"
        )
        delete_url = reverse("attendance:delete_student", args=[student.id])

        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Student.objects.filter(id=student.id).exists())

        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse("attendance:student_list"))
        self.assertFalse(Student.objects.filter(id=student.id).exists())

    def test_student_list_is_paginated_by_ten(self):
        Student.objects.bulk_create([
            Student(student_id=f"PAGE{i:02d}", name=f"Student {i}", email=f"student{i}@example.com")
            for i in range(15)
        ])
        first_page = self.client.get(reverse("attendance:student_list"))
        second_page = self.client.get(reverse("attendance:student_list"), {"page": 2})
        self.assertEqual(len(first_page.context["students"]), 10)
        self.assertEqual(len(second_page.context["students"]), 5)
        self.assertContains(first_page, "Showing 1&ndash;10 of 15 students", html=True)

    def test_student_list_searches_id_name_and_email(self):
        Student.objects.create(student_id="SEARCH01", name="Unique Student", email="unique-search@example.com")
        Student.objects.create(student_id="OTHER01", name="Other Student", email="other@example.com")
        response = self.client.get(reverse("attendance:student_list"), {"q": "unique-search"})
        self.assertContains(response, "Unique Student")
        self.assertNotContains(response, "Other Student")

    def test_student_id_is_unique_but_case_sensitive(self):
        Student.objects.create(student_id="STU200", name="First", email="first@example.com")

        response = self.client.post(
            reverse("attendance:register_student"),
            {"student_id": "stu200", "name": "Second", "email": "second@example.com"},
        )

        lowercase_student = Student.objects.get(student_id="stu200")
        self.assertRedirects(response, reverse("attendance:capture_face", args=[lowercase_student.id]))
        self.assertEqual(Student.objects.filter(student_id__in=["STU200", "stu200"]).count(), 2)

        duplicate_response = self.client.post(
            reverse("attendance:register_student"),
            {"student_id": "STU200", "name": "Duplicate", "email": "duplicate@example.com"},
        )
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertContains(duplicate_response, "A student with this ID already exists.")


class AdminCrudTests(TestCase):
    def setUp(self):
        self.current_admin = AdminUser(username="owner", email="owner@example.com")
        self.current_admin.set_password("owner-password")
        self.current_admin.save()
        self.client.cookies["access_token"] = create_access_token(self.current_admin)

    def test_create_and_view_admin(self):
        response = self.client.post(
            reverse("attendance:create_admin"),
            {
                "username": "manager",
                "email": "manager@example.com",
                "password": "manager-password",
                "confirm_password": "manager-password",
            },
        )
        self.assertEqual(response.status_code, 200)
        admin_user = AdminUser.objects.get(username="manager")
        self.assertTrue(admin_user.check_password("manager-password"))

        response = self.client.get(reverse("attendance:admin_detail", args=[admin_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "manager@example.com")

    def test_update_admin_and_optional_password(self):
        admin_user = AdminUser(username="editor", email="editor@example.com")
        admin_user.set_password("old-password")
        admin_user.save()

        response = self.client.post(
            reverse("attendance:update_admin", args=[admin_user.id]),
            {
                "username": "updated-editor",
                "email": "updated@example.com",
                "is_active": "on",
                "password": "new-password",
                "confirm_password": "new-password",
            },
        )
        self.assertRedirects(response, reverse("attendance:admin_detail", args=[admin_user.id]))
        admin_user.refresh_from_db()
        self.assertEqual(admin_user.username, "updated-editor")
        self.assertTrue(admin_user.check_password("new-password"))

    def test_delete_admin_but_not_current_admin(self):
        other_admin = AdminUser.objects.create(username="delete-admin", email="delete-admin@example.com", password="unused")
        response = self.client.post(reverse("attendance:delete_admin", args=[other_admin.id]))
        self.assertRedirects(response, reverse("attendance:admin_list"))
        self.assertFalse(AdminUser.objects.filter(id=other_admin.id).exists())

        response = self.client.post(reverse("attendance:delete_admin", args=[self.current_admin.id]))
        self.assertRedirects(response, reverse("attendance:admin_detail", args=[self.current_admin.id]))
        self.assertTrue(AdminUser.objects.filter(id=self.current_admin.id).exists())

    def test_current_admin_cannot_deactivate_self(self):
        response = self.client.post(
            reverse("attendance:update_admin", args=[self.current_admin.id]),
            {"username": "owner", "email": "owner@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You cannot deactivate your own signed-in account.")
        self.current_admin.refresh_from_db()
        self.assertTrue(self.current_admin.is_active)

    def test_admin_list_is_paginated_by_ten(self):
        AdminUser.objects.bulk_create([
            AdminUser(username=f"admin{i:02d}", email=f"admin{i}@example.com", password="unused")
            for i in range(14)
        ])
        first_page = self.client.get(reverse("attendance:admin_list"))
        second_page = self.client.get(reverse("attendance:admin_list"), {"page": 2})
        self.assertEqual(len(first_page.context["admins"]), 10)
        self.assertEqual(len(second_page.context["admins"]), 5)
        self.assertContains(first_page, "Showing 1&ndash;10 of 15 admins", html=True)

    def test_admin_list_searches_username_and_email(self):
        AdminUser.objects.create(username="search-manager", email="find-manager@example.com", password="unused")
        AdminUser.objects.create(username="other-manager", email="other-manager@example.com", password="unused")
        response = self.client.get(reverse("attendance:admin_list"), {"q": "find-manager"})
        self.assertContains(response, "search-manager")
        self.assertNotContains(response, "other-manager")


class AttendanceControlTests(TestCase):
    def setUp(self):
        self.admin = AdminUser(username="controller", email="controller@example.com")
        self.admin.set_password("controller-password")
        self.admin.save()
        self.client.cookies["access_token"] = create_access_token(self.admin)
        self.control_url = reverse("attendance:set_attendance_control")

    def test_admin_can_start_and_stop_student_attendance(self):
        start_response = self.client.post(self.control_url, {"action": "start"})
        self.assertEqual(start_response.status_code, 200)
        self.assertTrue(start_response.json()["is_open"])
        control = AttendanceControl.objects.get(pk=1)
        self.assertTrue(control.is_open)
        self.assertEqual(control.updated_by, self.admin)

        stop_response = self.client.post(self.control_url, {"action": "stop"})
        self.assertEqual(stop_response.status_code, 200)
        self.assertFalse(stop_response.json()["is_open"])
        control.refresh_from_db()
        self.assertFalse(control.is_open)

    def test_student_camera_and_api_are_blocked_while_closed(self):
        AttendanceControl.objects.create(pk=1, is_open=False)
        page_response = self.client.get(reverse("attendance:student_recognition_page"))
        self.assertContains(page_response, 'data-open="false"')

        api_response = self.client.post(reverse("attendance:student_recognize_face"))
        self.assertEqual(api_response.status_code, 403)
        self.assertEqual(api_response.json()["message"], "Attendance is currently closed by the administrator.")

    def test_attendance_control_requires_admin_login(self):
        self.client.cookies.clear()
        response = self.client.post(self.control_url, {"action": "start"})
        self.assertRedirects(response, reverse("attendance:admin_login"))


class StudentAPITests(TestCase):
    def setUp(self):
        self.admin = AdminUser(username="api-admin", email="api-admin@example.com")
        self.admin.set_password("api-password")
        self.admin.save()
        self.client.cookies["access_token"] = create_access_token(self.admin)
        self.list_url = reverse("attendance:student_api_list")

    def test_student_api_crud_uses_serializer(self):
        create_response = self.client.post(
            self.list_url,
            {"student_id": "API001", "name": "API Student", "email": "api-student@example.com"},
        )
        self.assertEqual(create_response.status_code, 201)
        student_id = create_response.json()["id"]
        detail_url = reverse("attendance:student_api_detail", args=[student_id])

        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["student_id"], "API001")
        self.assertIn("attendance_records", detail_response.json())

        update_response = self.client.patch(
            detail_url,
            {"name": "Updated API Student"},
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["name"], "Updated API Student")

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(Student.objects.filter(id=student_id).exists())

    def test_student_api_requires_admin_cookie(self):
        self.client.cookies.clear()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 403)

    def test_student_api_is_paginated_by_ten(self):
        Student.objects.bulk_create([
            Student(student_id=f"API{i:02d}", name=f"API {i}", email=f"api{i}@example.com")
            for i in range(12)
        ])
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 12)
        self.assertEqual(len(response.json()["results"]), 10)


class AdminAPITests(TestCase):
    def setUp(self):
        self.current_admin = AdminUser(username="api-owner", email="api-owner@example.com")
        self.current_admin.set_password("owner-password")
        self.current_admin.save()
        self.client.cookies["access_token"] = create_access_token(self.current_admin)
        self.list_url = reverse("attendance:admin_api_list")

    def test_admin_api_crud_hashes_password(self):
        create_response = self.client.post(
            self.list_url,
            {"username": "api-manager", "email": "api-manager@example.com", "password": "manager-password"},
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertNotIn("password", create_response.json())
        admin_user = AdminUser.objects.get(username="api-manager")
        self.assertTrue(admin_user.check_password("manager-password"))
        detail_url = reverse("attendance:admin_api_detail", args=[admin_user.id])

        update_response = self.client.patch(
            detail_url,
            {"email": "updated-manager@example.com", "password": "updated-password"},
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200)
        admin_user.refresh_from_db()
        self.assertEqual(admin_user.email, "updated-manager@example.com")
        self.assertTrue(admin_user.check_password("updated-password"))

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(AdminUser.objects.filter(id=admin_user.id).exists())

    def test_admin_cannot_delete_or_deactivate_self_through_api(self):
        detail_url = reverse("attendance:admin_api_detail", args=[self.current_admin.id])
        deactivate_response = self.client.patch(
            detail_url, {"is_active": False}, content_type="application/json"
        )
        self.assertEqual(deactivate_response.status_code, 400)
        self.current_admin.refresh_from_db()
        self.assertTrue(self.current_admin.is_active)

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, 403)
        self.assertTrue(AdminUser.objects.filter(id=self.current_admin.id).exists())

    def test_admin_api_requires_password_on_create(self):
        response = self.client.post(
            self.list_url,
            {"username": "no-password", "email": "no-password@example.com"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json())


class StudentFileSignalTests(TestCase):
    def test_deleting_student_removes_photo_dataset_and_class_name(self):
        with TemporaryDirectory() as temporary_directory:
            base_dir = Path(temporary_directory)
            media_root = base_dir / "media"
            classes_path = base_dir / "ml_models" / "class_names.json"
            classes_path.parent.mkdir(parents=True)
            classes_path.write_text(json.dumps(["KEEP", "DELETE01"]))

            with self.settings(BASE_DIR=base_dir, MEDIA_ROOT=media_root):
                student = Student.objects.create(
                    student_id="DELETE01",
                    name="Delete Files",
                    email="delete-files@example.com",
                    photo=SimpleUploadedFile("delete.jpg", b"photo-data", content_type="image/jpeg"),
                )
                photo_path = Path(student.photo.path)
                dataset_folder = base_dir / "dataset" / "DELETE01"
                dataset_folder.mkdir(parents=True)
                (dataset_folder / "face_001.jpg").write_bytes(b"face-data")

                with self.captureOnCommitCallbacks(execute=True):
                    student.delete()

                self.assertFalse(photo_path.exists())
                self.assertFalse(dataset_folder.exists())
                self.assertEqual(json.loads(classes_path.read_text()), ["KEEP"])

    def test_updating_student_replaces_photo_and_renames_dataset_class(self):
        with TemporaryDirectory() as temporary_directory:
            base_dir = Path(temporary_directory)
            media_root = base_dir / "media"
            classes_path = base_dir / "ml_models" / "class_names.json"
            classes_path.parent.mkdir(parents=True)
            classes_path.write_text(json.dumps(["OLD01", "KEEP"]))

            with self.settings(BASE_DIR=base_dir, MEDIA_ROOT=media_root):
                student = Student.objects.create(
                    student_id="OLD01",
                    name="Update Files",
                    email="update-files@example.com",
                    photo=SimpleUploadedFile("old.jpg", b"old-photo", content_type="image/jpeg"),
                )
                old_photo_path = Path(student.photo.path)
                old_dataset = base_dir / "dataset" / "OLD01"
                old_dataset.mkdir(parents=True)
                (old_dataset / "face_001.jpg").write_bytes(b"face-data")

                student.student_id = "NEW01"
                student.photo = SimpleUploadedFile("new.jpg", b"new-photo", content_type="image/jpeg")
                with self.captureOnCommitCallbacks(execute=True):
                    student.save()

                self.assertFalse(old_photo_path.exists())
                self.assertTrue(Path(student.photo.path).exists())
                self.assertFalse(old_dataset.exists())
                self.assertTrue((base_dir / "dataset" / "NEW01" / "face_001.jpg").exists())
                self.assertEqual(json.loads(classes_path.read_text()), ["NEW01", "KEEP"])
