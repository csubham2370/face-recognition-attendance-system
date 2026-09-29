import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings

def create_access_token(admin):

    payload = {
        "admin_id": admin.id,
        "username": admin.username,
        "email": admin.email,
        "token_type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def create_refresh_token(admin):

    payload = {
        "admin_id": admin.id,
        "username": admin.username,
        "token_type": "refresh",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def verify_token(token, expected_type=None):

    try:

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])

        if expected_type:

            if payload.get("token_type") != expected_type:
                return None

        return payload


    except jwt.ExpiredSignatureError:

        return None


    except jwt.InvalidTokenError:

        return None
