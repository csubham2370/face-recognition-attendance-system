from django.urls import path

from . import views
from .api_views import AdminDetailAPI, AdminListCreateAPI, StudentDetailAPI, StudentListCreateAPI
app_name = "attendance" 

urlpatterns = [
    path("api/students/", StudentListCreateAPI.as_view(), name="student_api_list"),
    path("api/students/<int:pk>/", StudentDetailAPI.as_view(), name="student_api_detail"),
    path("api/admins/", AdminListCreateAPI.as_view(), name="admin_api_list"),
    path("api/admins/<int:pk>/", AdminDetailAPI.as_view(), name="admin_api_detail"),
    path("", views.admin_login, name="home"),
    path("students/", views.student_list, name="student_list"),
    path("students/register/", views.register_student, name="register_student"),
    path("students/<int:student_id>/", views.student_detail, name="student_detail"),
    path("students/<int:student_id>/edit/", views.update_student, name="update_student"),
    path("students/<int:student_id>/delete/", views.delete_student, name="delete_student"),
    path("students/<int:student_id>/capture/", views.capture_face, name="capture_face"),
    path("students/<int:student_id>/capture/image/", views.capture_face_image, name="capture_face_image"),
    path("recognition/", views.recognition_page, name="recognition_page"),
    path("recognition/predict/", views.recognize_face, name="recognize_face"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/data/", views.dashboard_data, name="dashboard_data"),
    path("dashboard/attendance-control/", views.set_attendance_control, name="set_attendance_control"),
    path("admin-panel/login/", views.admin_login, name="admin_login"),
    path("admin-panel/logout/", views.admin_logout, name="admin_logout"),
    path("admin-panel/users/", views.admin_list, name="admin_list"),
    path("model/train/",views.train_model_view,name="train_model"),
    path("student/recognition/",views.student_recognition_page,name="student_recognition_page"),
    path("student/recognition/predict/",views.student_recognize_face,name="student_recognize_face"),
    path("admin-panel/create/",views.create_admin,name="create_admin"),
    path("admin-panel/users/<int:admin_id>/", views.admin_detail, name="admin_detail"),
    path("admin-panel/users/<int:admin_id>/edit/", views.update_admin, name="update_admin"),
    path("admin-panel/users/<int:admin_id>/delete/", views.delete_admin, name="delete_admin"),
    path("admin-panel/forgot-password/",views.forgot_password,name="forgot_password"),
    path("admin-panel/reset-password/<str:token>/",views.reset_password,name="reset_password"),
]
