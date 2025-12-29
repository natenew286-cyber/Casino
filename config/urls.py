from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Casino Backend API",
        default_version='v1',
        description="Production-ready casino backend API",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Health check (optional - requires django-health-check package)
    # path('health/', include('health_check.urls')),
    
    # API routes
    path('api/auth/', include('apps.accounts.urls')),
    path('api/wallet/', include('apps.wallet.urls')),
    path('api/games/', include('apps.games.urls')),
    path('api/admin/', include('apps.admin_panel.urls')),
    
    # Audit
    path('api/audit/', include('apps.audit.urls')),
]

# Admin site customization
admin.site.site_header = 'Casino Backend Administration'
admin.site.site_title = 'Casino Backend Admin'
admin.site.index_title = 'Welcome to Casino Backend Admin'