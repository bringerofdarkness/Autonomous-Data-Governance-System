from datetime import timedelta
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from app.core.config import get_settings
from app.core.security import create_access_token, verify_password

User = get_user_model()
settings = get_settings()


def authenticate_user(email: str, password: str) -> User:
    try:
        user = User.objects.prefetch_related("roles").get(email=email)
    except User.DoesNotExist:
        raise AuthenticationFailed("Invalid email or password.")

    if not user.is_active:
        raise AuthenticationFailed("User account is inactive.")

    # Using FastAPI's exact password verification logic for full backward compatibility
    if not verify_password(password, user.password):
        raise AuthenticationFailed("Invalid email or password.")

    return user


def create_user_access_token(user: User) -> str:
    user_roles = [role.name for role in user.roles.all()]

    return create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={
            "email": user.email,
            "roles": user_roles,
        },
    )