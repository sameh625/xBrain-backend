from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def api_root(request):
    return JsonResponse({
        "message": "Welcome to xBrain API",
        "status": "running",
        "endpoints": {
            "register": "/api/auth/register/",
            "verify_email": "/api/auth/verify-email/",
            "login": "/api/auth/login/",
            "resend_otp": "/api/auth/resend-otp/",
            "refresh_token": "/api/auth/token/refresh/",
            "profile": "/api/users/me/",
        }
    })


urlpatterns = [
    path("", api_root),  # Root URL - API info
    path("admin/", admin.site.urls),
    path("api/", include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

