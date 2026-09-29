from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.authentication import BaseAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission

from .jwt_utils import verify_token
from .models import AdminUser, Student
from .serializers import AdminSerializer, StudentDetailSerializer, StudentSerializer


class AdminCookieAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get("access_token")
        payload = verify_token(token, expected_type="access") if token else None
        if not payload:
            return None
        try:
            admin = AdminUser.objects.get(id=payload.get("admin_id"), is_active=True)
        except AdminUser.DoesNotExist:
            return None
        return admin, payload


class IsActiveAdmin(BasePermission):
    message = "Admin login required."

    def has_permission(self, request, view):
        return isinstance(request.user, AdminUser) and request.user.is_active


class StudentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class StudentListCreateAPI(generics.ListCreateAPIView):
    authentication_classes = [AdminCookieAuthentication]
    permission_classes = [IsActiveAdmin]
    pagination_class = StudentPagination
    serializer_class = StudentSerializer
    queryset = Student.objects.all().order_by("-created_at")


class StudentDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [AdminCookieAuthentication]
    permission_classes = [IsActiveAdmin]
    serializer_class = StudentDetailSerializer
    queryset = Student.objects.prefetch_related("attendance_records")


class AdminListCreateAPI(generics.ListCreateAPIView):
    authentication_classes = [AdminCookieAuthentication]
    permission_classes = [IsActiveAdmin]
    pagination_class = StudentPagination
    serializer_class = AdminSerializer
    queryset = AdminUser.objects.all().order_by("username")


class AdminDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [AdminCookieAuthentication]
    permission_classes = [IsActiveAdmin]
    serializer_class = AdminSerializer
    queryset = AdminUser.objects.all()

    def perform_destroy(self, instance):
        if instance.id == self.request.user.id:
            raise PermissionDenied("You cannot delete your own signed-in account.")
        instance.delete()
