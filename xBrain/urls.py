from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


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
    
    # Swagger Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if not settings.USE_AZURE_STORAGE:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

