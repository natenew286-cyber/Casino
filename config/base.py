import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Disable automatic slash appending for API routes
APPEND_SLASH = False

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-development-key')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'channels',
    'django_celery_beat',
    'guardian',
    'drf_yasg',
    
    # Local apps
    'apps.accounts',
    'apps.wallet',
    'apps.games',
    'apps.fraud',
    'apps.admin_panel',
    'apps.audit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'core.middleware.APICommonMiddleware',  # Custom CommonMiddleware that skips API routes
    'core.middleware.APIMiddleware',  # Custom API middleware to ensure JSON responses
    'core.middleware.APICsrfMiddleware',  # Custom CSRF middleware that exempts API routes and OPTIONS requests
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'casino_db'),
        'USER': os.getenv('DB_USER', 'casino_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'casino_password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Password hashing - Use Argon2 (Django 4.2+ has built-in Argon2 support)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'DEFAULT_PAGINATION_CLASS': 'core.utils.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME', 900))),
    'REFRESH_TOKEN_LIFETIME': timedelta(seconds=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME', 604800))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# Redis Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Log Redis configuration for debugging
import logging
logger = logging.getLogger(__name__)
redis_url_env = os.getenv('REDIS_URL', 'NOT SET - using default')
print(f"[REDIS CONFIG] REDIS_URL from environment: {redis_url_env}")
print(f"[REDIS CONFIG] REDIS_URL being used: {REDIS_URL}")
logger.info(f"REDIS_URL from environment: {redis_url_env}")
logger.info(f"REDIS_URL being used: {REDIS_URL}")

# Channels Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
            'capacity': 5000,
            'expiry': 10,
        },
    },
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

# Fix for Celery/Redis SSL issue: rediss:// URLs must have ssl_cert_reqs parameter
if CELERY_BROKER_URL.startswith('rediss://') and 'ssl_cert_reqs' not in CELERY_BROKER_URL:
    CELERY_BROKER_URL += '&ssl_cert_reqs=CERT_NONE' if '?' in CELERY_BROKER_URL else '?ssl_cert_reqs=CERT_NONE'

if CELERY_RESULT_BACKEND.startswith('rediss://') and 'ssl_cert_reqs' not in CELERY_RESULT_BACKEND:
    CELERY_RESULT_BACKEND += '&ssl_cert_reqs=CERT_NONE' if '?' in CELERY_RESULT_BACKEND else '?ssl_cert_reqs=CERT_NONE'

celery_broker_env = os.getenv('CELERY_BROKER_URL', 'NOT SET - using REDIS_URL')
celery_backend_env = os.getenv('CELERY_RESULT_BACKEND', 'NOT SET - using REDIS_URL')
print(f"[CELERY CONFIG] CELERY_BROKER_URL from environment: {celery_broker_env}")
print(f"[CELERY CONFIG] CELERY_BROKER_URL being used: {CELERY_BROKER_URL}")
print(f"[CELERY CONFIG] CELERY_RESULT_BACKEND from environment: {celery_backend_env}")
print(f"[CELERY CONFIG] CELERY_RESULT_BACKEND being used: {CELERY_RESULT_BACKEND}")
logger.info(f"CELERY_BROKER_URL from environment: {celery_broker_env}")
logger.info(f"CELERY_BROKER_URL being used: {CELERY_BROKER_URL}")
logger.info(f"CELERY_RESULT_BACKEND from environment: {celery_backend_env}")
logger.info(f"CELERY_RESULT_BACKEND being used: {CELERY_RESULT_BACKEND}")
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Guardian (object permissions)
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

# Security settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Audit logging
AUDIT_LOG_MODEL = 'audit.AuditLog'

# Email Configuration (supports Outlook, QQ, Gmail, etc.)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp-mail.outlook.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Frontend URL for password reset links
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# OTP Configuration
OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', '10'))
PASSWORD_RESET_TOKEN_EXPIRY_HOURS = int(os.getenv('PASSWORD_RESET_TOKEN_EXPIRY_HOURS', '1'))

# Custom settings
GAME_CONFIG = {
    'MIN_BET_AMOUNT': 0.01,
    'MAX_BET_AMOUNT': 10000.00,
    'DEFAULT_HOUSE_EDGE': 0.01,  # 1%
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False').lower() == 'true'
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000').split(',')
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
# Cache preflight requests for 1 hour (3600 seconds)
CORS_PREFLIGHT_MAX_AGE = 3600
# Expose headers to the client
CORS_EXPOSE_HEADERS = [
    "content-type",
    "authorization",
]

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000').split(',')
]