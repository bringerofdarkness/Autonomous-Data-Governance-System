import os
import uuid
from jose import jwt, JWTError
from rest_framework import authentication
from rest_framework import exceptions
from django.conf import settings
from app.models import User

class CustomJWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        try:
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return None
            token = parts[1]
        except Exception:
            return None

        try:
            # Decode JWT token using python-jose matching FastAPI setup
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[os.getenv("JWT_ALGORITHM", "HS256")],
            )
            user_id = payload.get("sub")
            if user_id is None:
                raise exceptions.AuthenticationFailed("Invalid token: Subject claim is missing.")
            
            user_uuid = uuid.UUID(user_id)
        except (JWTError, ValueError) as exc:
            raise exceptions.AuthenticationFailed(f"Invalid authentication token: {str(exc)}")

        try:
            user = User.objects.get(id=user_uuid)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("User not found.")

        if not user.is_active:
            raise exceptions.AuthenticationFailed("User account is inactive.")

        # In DRF, returning (user, auth) sets request.user and request.auth
        return (user, token)
