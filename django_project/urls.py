from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django Admin Panel
    path("admin/", admin.site.urls),
    
    # ADGS API endpoints at root level to match FastAPI paths exactly
    path("", include("app.urls")),
]
