from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from app.core.security import verify_password

User = get_user_model()


class ADGSAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if not username or not password:
            return None
            
        try:
            # Query the custom User model
            user = User.objects.prefetch_related("roles").get(email=username)
            
            # Verify password using the exact verify_password method from security.py
            if verify_password(password, user.password):
                return user
        except User.DoesNotExist:
            return None
        except Exception:
            return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.prefetch_related("roles").get(pk=user_id)
        except User.DoesNotExist:
            return None
