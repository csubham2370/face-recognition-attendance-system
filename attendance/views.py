from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest,HttpResponse
from .forms import StudentForm, AdminLoginForm, CreateAdminForm, UpdateAdminForm
from .models import Student, Attendance, AdminUser, AttendanceControl
import cv2
import numpy as np
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .decorators import admin_required
from django.views.decorators.cache import never_cache
from .jwt_utils import create_access_token, create_refresh_token, verify_token
import secrets
import logging
from pathlib import Path
from smtplib import SMTPException
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse


logger = logging.getLogger(__name__)


@admin_required
def register_student(request:HttpRequest) -> HttpResponse:

    if request.method == "POST":

        form = StudentForm(request.POST,request.FILES)

        if form.is_valid():

            student = form.save()

            messages.success(request, f"{student.name} was registered. Now capture 30 face photos.")

            return redirect("attendance:capture_face", student_id=student.id)

    else:

        form = StudentForm()

    return render(request, "attendance/register_student.html",{"form": form, "student": None})

@admin_required
def student_list(request:HttpRequest) -> HttpResponse:

    student_queryset = Student.objects.all().order_by("-created_at")
    search_query = request.GET.get("q", "").strip()
    if search_query:
        student_queryset = student_queryset.filter(
            Q(student_id__icontains=search_query)
            | Q(name__icontains=search_query)
            | Q(email__icontains=search_query)
        )
    students = Paginator(student_queryset, 10).get_page(request.GET.get("page"))

    return render(
        request,
        "attendance/student_list.html",
        {"students": students, "page_obj": students, "search_query": search_query},
    )


@admin_required
def student_detail(request: HttpRequest, student_id: int) -> HttpResponse:
    student = get_object_or_404(Student, id=student_id)
    attendance_records = student.attendance_records.order_by("-date", "-time")
    return render(
        request,
        "attendance/student_detail.html",
        {"student": student, "attendance_records": attendance_records},
    )


@admin_required
def update_student(request: HttpRequest, student_id: int) -> HttpResponse:
    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"{student.name}'s details were updated successfully.")
            return redirect("attendance:student_detail", student_id=student.id)
    else:
        form = StudentForm(instance=student)

    return render(
        request,
        "attendance/register_student.html",
        {"form": form, "student": student},
    )


@admin_required
def delete_student(request: HttpRequest, student_id: int) -> HttpResponse:
    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        student_name = student.name
        student.delete()
        messages.success(request, f"{student_name} was deleted successfully.")
        return redirect("attendance:student_list")

    return render(request, "attendance/student_confirm_delete.html", {"student": student})

@admin_required
def capture_face(request:HttpRequest, student_id:str) -> HttpResponse:

    student = get_object_or_404(Student,id=student_id)

    student_folder = Path(settings.BASE_DIR) / "dataset" / student.student_id
    captured_count = len(list(student_folder.glob("face_*.jpg"))) if student_folder.exists() else 0

    return render(
        request,
        "attendance/capture_face.html",
        {"student": student, "captured_count": min(captured_count, 30), "target_count": 30},
    )


@admin_required
@require_POST
def capture_face_image(request: HttpRequest, student_id: int) -> JsonResponse:
    student = get_object_or_404(Student, id=student_id)
    uploaded_image = request.FILES.get("image")

    if not uploaded_image:
        return JsonResponse({"success": False, "message": "Camera image was not received."}, status=400)

    student_folder = Path(settings.BASE_DIR) / "dataset" / student.student_id
    student_folder.mkdir(parents=True, exist_ok=True)

    if request.POST.get("reset") == "true":
        for old_image in student_folder.glob("face_*.jpg"):
            old_image.unlink()

    existing_images = sorted(student_folder.glob("face_*.jpg"))
    if len(existing_images) >= 30:
        return JsonResponse({"success": True, "captured_count": 30, "complete": True})

    image_bytes = np.frombuffer(uploaded_image.read(), np.uint8)
    frame = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
    if frame is None:
        return JsonResponse({"success": False, "message": "The camera image is invalid."}, status=400)

    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cascade_classifier = getattr(cv2, "CascadeClassifier", None)
    if cascade_classifier is not None:
        detector = cascade_classifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = detector.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
        if len(faces) != 1:
            message = "No face detected. Look directly at the camera." if len(faces) == 0 else "Only one person may be visible."
            return JsonResponse(
                {"success": False, "message": message, "captured_count": len(existing_images)},
                status=422,
            )
        x, y, width, height = faces[0]
        face_image = gray_frame[y:y + height, x:x + width]
    else:
        # Some OpenCV builds omit Haar cascades. The capture UI keeps the face
        # centered, so use the largest centered square as a compatible fallback.
        frame_height, frame_width = gray_frame.shape
        crop_size = min(frame_height, frame_width)
        x = (frame_width - crop_size) // 2
        y = (frame_height - crop_size) // 2
        face_image = gray_frame[y:y + crop_size, x:x + crop_size]
    if face_image.size == 0:
        return JsonResponse({"success": False, "message": "Unable to crop the detected face."}, status=422)

    face_image = cv2.resize(face_image, (200, 200))
    sharpness = float(cv2.Laplacian(face_image, cv2.CV_64F).var())
    if sharpness < 30:
        return JsonResponse(
            {
                "success": False,
                "message": "The image is blurry. Hold still and improve the lighting.",
                "captured_count": len(existing_images),
            },
            status=422,
        )

    next_count = len(existing_images) + 1
    image_path = student_folder / f"face_{next_count:03d}.jpg"
    if not cv2.imwrite(str(image_path), face_image):
        return JsonResponse({"success": False, "message": "Unable to save the face photo."}, status=500)

    return JsonResponse(
        {
            "success": True,
            "captured_count": next_count,
            "complete": next_count >= 30,
            "message": "All 30 face photos were captured." if next_count >= 30 else "Face photo captured.",
        }
    )

@admin_required
def recognition_page(request:HttpRequest) -> HttpResponse:

    return render(request,"attendance/recognition.html")

@require_POST
def recognize_face(request:HttpRequest) -> JsonResponse:

    try:

        from .ml.predictor import predict_face

    except (ImportError, ModuleNotFoundError):

        return JsonResponse(
            {
                "success": False,
                "message": "Face recognition is unavailable because the ML runtime is not installed."
            },
            status=503
        )

    uploaded_image = request.FILES.get("image")

    if not uploaded_image:

        return JsonResponse({"success": False,"message": "Image not received."},status=400)

    image_bytes = np.frombuffer(uploaded_image.read(), np.uint8)

    image = cv2.imdecode(image_bytes,cv2.IMREAD_COLOR)


    if image is None:

        return JsonResponse({"success": False,"message": "Invalid image." },status=400)

    # OpenCV + CNN
    result = predict_face(image)

    if not result["success"]:

        return JsonResponse(result)

    student_id = result["student_id"]

    # Find student
    try:

        student = Student.objects.get(student_id=student_id)

    except Student.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message":"Student not found in database."
            }
        )

    # Current local date/time
    current_time = timezone.localtime()

    today = current_time.date()

    # --------------------------------
    # Create attendance only once
    # --------------------------------

    attendance, created = (
        Attendance.objects.get_or_create(student=student,date=today,
            defaults={
                "time": current_time.time(),
                "status": "Present",
                "confidence":result["confidence"]
            }
        )
    )


    # --------------------------------
    # Response
    # --------------------------------

    if created:

        attendance_message = ("Attendance marked successfully.")

    else:

        attendance_message = ("Attendance already marked today.")

    return JsonResponse(
        {
            "success": True,
            "student_id": student.student_id,
            "name":student.name,
            "email":student.email,
            "confidence":round(result["confidence"],2),
            "attendance_created":created,
            "attendance_message":attendance_message,
            "date":attendance.date.strftime("%d-%m-%Y"),
            "time":attendance.time.strftime("%I:%M:%S %p")
        }
    )

@admin_required
def dashboard(request: HttpRequest) -> HttpResponse:
    attendance_control, _ = AttendanceControl.objects.get_or_create(pk=1)
    return render(
        request,
        "attendance/dashboard.html",
        {"admin": request.admin, "attendance_control": attendance_control},
    )


@admin_required
@require_POST
def set_attendance_control(request: HttpRequest) -> JsonResponse:
    action = request.POST.get("action")
    if action not in {"start", "stop"}:
        return JsonResponse({"success": False, "message": "Invalid attendance action."}, status=400)

    attendance_control, _ = AttendanceControl.objects.get_or_create(pk=1)
    attendance_control.is_open = action == "start"
    attendance_control.updated_by = request.admin
    attendance_control.save(update_fields=["is_open", "updated_by", "updated_at"])
    state = "started" if attendance_control.is_open else "stopped"
    return JsonResponse(
        {
            "success": True,
            "is_open": attendance_control.is_open,
            "message": f"Student attendance has been {state}.",
        }
    )

@admin_required
def dashboard_data(request:HttpRequest) -> JsonResponse:

    today = timezone.localdate()
    # Total students
    total_students = Student.objects.count()
    # Today's attendance
    today_records = Attendance.objects.filter(date=today)
    # Present students
    present_count = today_records.count()
    # Absent students
    absent_count = total_students - present_count
    # Prevent negative value
    if absent_count < 0:
        absent_count = 0
    # Attendance percentage
    if total_students > 0:

        attendance_percentage = (present_count / total_students) * 100
    else:
        attendance_percentage = 0

    # Recent attendance
    recent_records = (Attendance.objects.select_related("student").order_by("-date", "-time")[:5])

    recent_attendance = []

    for record in recent_records:

        recent_attendance.append({

            "student_id":record.student.student_id,
            "name":record.student.name,
            "date":record.date.strftime("%d-%m-%Y"),
            "time":record.time.strftime("%I:%M:%S %p"),
            "status":record.status,
            "confidence":round(record.confidence or 0, 2)
        })


    return JsonResponse({
            "success": True,
            "total_students":total_students,
            "present_count":present_count,
            "absent_count":absent_count,
            "attendance_percentage":round(attendance_percentage,2),
            "today":today.strftime("%d-%m-%Y"),
            "recent_attendance":recent_attendance
        }
    )

@never_cache
def admin_login(request:HttpRequest) -> JsonResponse:

    access_token = request.COOKIES.get("access_token")

    if access_token:

        payload = verify_token(access_token, expected_type="access")

        if payload:

            return redirect("attendance:dashboard")

    if request.method == "POST":

        username = request.POST.get("username","").strip()
        password = request.POST.get("password","")

        if not username or not password:

            return JsonResponse({
                "success": False,
                "message": "Username and password are required."
            })

        try:

            admin = AdminUser.objects.get(username=username)

        except AdminUser.DoesNotExist:

            return JsonResponse({
                "success": False,
                "message": "Invalid username or password."
            })


        if not admin.is_active:

            return JsonResponse({
                "success": False,
                "message": "Your admin account is inactive."
            })


        if not admin.check_password(password):

            return JsonResponse({
                "success": False,
                "message": "Invalid username or password."
            })

        # Create JWT tokens
        access_token = create_access_token(admin)
        refresh_token = create_refresh_token(admin)
        response = JsonResponse({
            "success": True,
            "message": "Login successful.",
            "redirect_url": "/dashboard/"
        })
        response.set_cookie(key="access_token", value=access_token, max_age=15 * 60, httponly=True, secure=False, samesite="Lax")
        response.set_cookie(key="refresh_token", value=refresh_token, max_age=7 * 24 * 60 * 60, httponly=True, secure=False, samesite="Lax")
        return response
    return render(request, "attendance/admin/login.html")

@never_cache
def admin_logout(request:HttpRequest) -> HttpResponse:

     response = redirect("attendance:admin_login")
     response.delete_cookie("access_token")
     response.delete_cookie("refresh_token")
     return response

@admin_required
def train_model_view(request:HttpRequest) -> HttpResponse:

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False,
                "message": "POST request required."
            },
            status=405
        )

    try:

        from .ml.predictor import reload_model
        from .ml.train_model import train_face_model

        result = train_face_model()

        reload_model()

        return JsonResponse(
            {
                "success": True,
                "message": "Model trained successfully.",
                "result": result
            }
        )

    except Exception as error:

        return JsonResponse(
            {
                "success": False,
                "message": str(error)
            },
            status=500
        )


def student_recognition_page(request:HttpRequest) -> HttpResponse:
    attendance_control, _ = AttendanceControl.objects.get_or_create(pk=1)
    return render(
        request,
        "attendance/student_recognition.html",
        {"attendance_is_open": attendance_control.is_open},
    )


def student_recognize_face(request:HttpRequest) -> JsonResponse:

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False,
                "message": "POST request required."
            },
            status=405
        )

    attendance_control, _ = AttendanceControl.objects.get_or_create(pk=1)
    if not attendance_control.is_open:
        return JsonResponse(
            {"success": False, "message": "Attendance is currently closed by the administrator."},
            status=403,
        )

    return recognize_face(request)

def process_face_recognition(request:HttpRequest) -> JsonResponse:

    try:
        from .ml.predictor import predict_face
    except (ImportError, ModuleNotFoundError):
        return JsonResponse(
            {
                "success": False,
                "message": "Face recognition is unavailable because the ML runtime is not installed."
            },
            status=503
        )

    uploaded_image = request.FILES.get("image")

    if not uploaded_image:

        return JsonResponse(
            {
                "success": False,
                "message": "Image not received."
            },
            status=400
        )


    image_bytes = np.frombuffer(uploaded_image.read(),np.uint8)

    image = cv2.imdecode(image_bytes,cv2.IMREAD_COLOR)


    if image is None:

        return JsonResponse(
            {
                "success": False,
                "message": "Invalid image."
            },
            status=400
        )


    # OpenCV + CNN
    result = predict_face(image)

    if not result["success"]:

        return JsonResponse(result)

    student_id = result["student_id"]

    # Find student
    try:

        student = Student.objects.get(student_id=student_id)

    except Student.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": "Student not found in database."
            }
        )


    current_time = timezone.localtime()

    today = current_time.date()


    attendance, created = Attendance.objects.get_or_create(student=student,date=today,
        defaults={"time": current_time.time(),"status": "Present","confidence": result["confidence"]}
    )


    if created:

        attendance_message = ("Attendance marked successfully.")

    else:

        attendance_message = ("Attendance already marked today.")


    return JsonResponse(
        {
            "success": True,
            "student_id": student.student_id,
            "name": student.name,
            "email": student.email,
            "confidence": round(result["confidence"],2),
            "attendance_created": created,
            "attendance_message": attendance_message,
            "date": attendance.date.strftime("%d-%m-%Y"),
            "time": attendance.time.strftime("%I:%M:%S %p")
        }
    )


@admin_required
def admin_list(request: HttpRequest) -> HttpResponse:
    admin_queryset = AdminUser.objects.all().order_by("username")
    search_query = request.GET.get("q", "").strip()
    if search_query:
        admin_queryset = admin_queryset.filter(
            Q(username__icontains=search_query) | Q(email__icontains=search_query)
        )
    admins = Paginator(admin_queryset, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "attendance/admin_list.html",
        {"admins": admins, "page_obj": admins, "search_query": search_query},
    )


@admin_required
def admin_detail(request: HttpRequest, admin_id: int) -> HttpResponse:
    admin_user = get_object_or_404(AdminUser, id=admin_id)
    return render(request, "attendance/admin_detail.html", {"admin_user": admin_user})


@admin_required
def create_admin(request):

    if request.method == "POST":

        form = CreateAdminForm(request.POST)

        if not form.is_valid():

            return JsonResponse(
                {
                    "success": False,
                    "message": form.errors.get_json_data()
                },
                status=400
            )

        username = form.cleaned_data["username"]
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]

        # Check username
        if AdminUser.objects.filter(username__iexact=username).exists():

            return JsonResponse(
                {
                    "success": False,
                    "message": "Username already exists."
                },
                status=400
            )


        # Check email
        if AdminUser.objects.filter(email__iexact=email).exists():

            return JsonResponse(
                {
                    "success": False,
                    "message": "Email already exists."
                },
                status=400
            )

        admin = AdminUser(username=username,email=email)

        admin.set_password(password)
        admin.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Admin created successfully.",
                "redirect_url": reverse("attendance:admin_detail", kwargs={"admin_id": admin.id}),
            }
        )


    form = CreateAdminForm()


    return render(request,"attendance/create_admin.html",{"form": form})


@admin_required
def update_admin(request: HttpRequest, admin_id: int) -> HttpResponse:
    admin_user = get_object_or_404(AdminUser, id=admin_id)
    if request.method == "POST":
        form = UpdateAdminForm(request.POST, instance=admin_user)
        if form.is_valid():
            if admin_user.id == request.admin.id and not form.cleaned_data["is_active"]:
                form.add_error("is_active", "You cannot deactivate your own signed-in account.")
            else:
                admin_user = form.save()
                messages.success(request, f"{admin_user.username}'s account was updated successfully.")
                return redirect("attendance:admin_detail", admin_id=admin_user.id)
    else:
        form = UpdateAdminForm(instance=admin_user)
    return render(request, "attendance/admin_form.html", {"form": form, "admin_user": admin_user})


@admin_required
def delete_admin(request: HttpRequest, admin_id: int) -> HttpResponse:
    admin_user = get_object_or_404(AdminUser, id=admin_id)
    if admin_user.id == request.admin.id:
        messages.error(request, "You cannot delete your own signed-in account.")
        return redirect("attendance:admin_detail", admin_id=admin_user.id)
    if request.method == "POST":
        username = admin_user.username
        admin_user.delete()
        messages.success(request, f"{username}'s admin account was deleted successfully.")
        return redirect("attendance:admin_list")
    return render(request, "attendance/admin_confirm_delete.html", {"admin_user": admin_user})


def forgot_password(request):

    if request.method == "POST":

        email = request.POST.get("email","").strip()

        if not email:

            return JsonResponse(
                {
                    "success": False,
                    "message": "Email is required."
                },
                status=400
            )

        try:

            admin = AdminUser.objects.get(email__iexact=email)

        except AdminUser.DoesNotExist:

            return JsonResponse(
                {
                    "success": False,
                    "message": "No admin account found with this email."
                },
                status=404
            )


        reset_token = secrets.token_urlsafe(32)
        admin.reset_token = reset_token
        admin.reset_token_created_at = timezone.now()
        admin.save(update_fields=["reset_token","reset_token_created_at"])

        reset_url = request.build_absolute_uri(reverse("attendance:reset_password",kwargs={"token": reset_token}))

        try:
            sent_count = send_mail(subject="Admin Password Reset",
                message=(f"Hello {admin.username},\n\n"
                    "Click the link below to reset your password:\n\n"
                    f"{reset_url}\n\n"
                    "If you did not request this, ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
                fail_silently=False
            )
        except (SMTPException, OSError):
            logger.exception("Unable to send password-reset email to admin ID %s", admin.pk)
            admin.reset_token = None
            admin.reset_token_created_at = None
            admin.save(update_fields=["reset_token", "reset_token_created_at"])
            return JsonResponse(
                {
                    "success": False,
                    "message": "The reset email could not be sent. Please check the email settings and try again."
                },
                status=503
            )

        if sent_count != 1:
            admin.reset_token = None
            admin.reset_token_created_at = None
            admin.save(update_fields=["reset_token", "reset_token_created_at"])
            return JsonResponse(
                {
                    "success": False,
                    "message": "The email service did not accept the reset email. Please try again."
                },
                status=503
            )


        return JsonResponse(
            {
                "success": True,
                "message": "Password reset link sent to your email."
            }
        )


    return render(
        request,
        "attendance/forgot_password.html"
    )


def reset_password(request, token):

    try:
        admin = AdminUser.objects.get(reset_token=token)
    except AdminUser.DoesNotExist:
        admin = None

    token_is_valid = (
        admin is not None
        and admin.reset_token_created_at is not None
        and admin.reset_token_created_at >= timezone.now() - timedelta(hours=1)
    )

    if request.method == "POST":

        if not token_is_valid:
            return JsonResponse(
                {"success": False, "message": "This reset link is invalid or has expired."},
                status=400,
            )

        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if len(password) < 8:
            return JsonResponse(
                {"success": False, "message": "Password must contain at least 8 characters."},
                status=400,
            )

        if password != confirm_password:
            return JsonResponse(
                {"success": False, "message": "Passwords do not match."},
                status=400,
            )

        admin.set_password(password)
        admin.reset_token = None
        admin.reset_token_created_at = None
        admin.save(update_fields=["password", "reset_token", "reset_token_created_at"])

        return JsonResponse(
            {"success": True, "message": "Password reset successfully."}
        )

    return render(
        request,
        "attendance/reset_password.html",
        {"token_is_valid": token_is_valid},
        status=200 if token_is_valid else 400,
    )
