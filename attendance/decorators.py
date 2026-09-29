from functools import wraps

from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

from .models import AdminUser
from .jwt_utils import create_access_token, verify_token


def unauthorized_response(request):

    if request.headers.get("x-requested-with") == "XMLHttpRequest":

        response = JsonResponse(
            {
                "success": False,
                "message": "Admin login required."
            },
            status=401
        )
    return redirect("attendance:admin_login")


def admin_required(view_func):

    @wraps(view_func)
    @never_cache
    def wrapper(request, *args, **kwargs):

        access_token = request.COOKIES.get("access_token")
        refresh_token = request.COOKIES.get("refresh_token")


        # --------------------------------
        # Check Access Token
        # --------------------------------

        access_payload = None

        if access_token:

            access_payload = verify_token(access_token,expected_type="access")


        # --------------------------------
        # Access token expired/invalid
        # Try Refresh Token
        # --------------------------------

        new_access_token = None

        if not access_payload:

            if not refresh_token:

                return unauthorized_response(request)


            refresh_payload = verify_token(refresh_token,expected_type="refresh")


            if not refresh_payload:

                return unauthorized_response(request)

            admin_id = refresh_payload.get("admin_id")

            try:

                admin = AdminUser.objects.get( id=admin_id,is_active=True)

            except AdminUser.DoesNotExist:

                return unauthorized_response(request)

            # Create new access token

            new_access_token = (create_access_token(admin))
        else:

            # Access token is valid

            admin_id = access_payload.get("admin_id")

            try:

                admin = AdminUser.objects.get(id=admin_id,is_active=True)

            except AdminUser.DoesNotExist:

                return unauthorized_response(request)

        # Make admin available to view

        request.admin = admin

        # Run original view

        response = view_func(request, *args, **kwargs )

        # --------------------------------
        # Set new Access Token
        # --------------------------------

        if new_access_token:

            response.set_cookie(key="access_token",value=new_access_token,max_age=15 * 60,httponly=True,secure=False,samesite="Lax")

        return response


    return wrapper
