"""
Enhanced security settings for MealPrepAI Django backend.
"""
import os
from .base import *

# Security Keys Management
class SecureKeyManager:
    """Manage secure generation and validation of API keys."""
    
    @staticmethod
    def generate_secure_key(length: int = 50) -> str:
        """Generate cryptographically secure random key."""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + '-_'
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def validate_key_strength(key: str) -> bool:
        """Validate key strength."""
        if len(key) < 32:
            return False
        if key in ['django-insecure-change-me-in-production', 'change-me']:
            return False
        return True

# Enhanced SECRET_KEY validation
if not SecureKeyManager.validate_key_strength(SECRET_KEY):
    import warnings
    warnings.warn(
        "Weak SECRET_KEY detected. Please generate a strong key for production.",
        UserWarning
    )

# Security Middleware Configuration
SECURITY_MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'common.middleware.SecurityHeadersMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'common.middleware.JWTAuthenticationMiddleware',
    'common.middleware.RequestLoggingMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Enhanced Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_PRELOAD = True

# Session Security
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 hour

# CSRF Protection
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_USE_SESSIONS = True
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:9002',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:9002',
]

# Password Validation (using original Django defaults)
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

# API Security Configuration
API_SECURITY = {
    'RATE_LIMITING': {
        'ENABLED': True,
        'DEFAULT_RATE': '100/hour',
        'AUTH_RATE': '1000/hour',
        'BURST_RATE': '10/minute',
    },
    'INPUT_VALIDATION': {
        'MAX_REQUEST_SIZE': 1024 * 1024,  # 1MB
        'MAX_FIELD_LENGTH': 2000,
        'ALLOWED_FILE_TYPES': ['image/jpeg', 'image/png', 'image/webp'],
        'MAX_FILE_SIZE': 5 * 1024 * 1024,  # 5MB
    },
    'CONTENT_SECURITY': {
        'SANITIZE_HTML': True,
        'VALIDATE_JSON': True,
        'BLOCK_SUSPICIOUS_PATTERNS': True,
    }
}

# Enhanced JWT Security
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),  # Reduced from 30 days
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': 'mealprep-api',
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# API Key Security
API_KEY_VALIDATION = {
    'GOOGLE_API_KEY': {
        'REQUIRED': True,
        'MIN_LENGTH': 30,
        'PATTERN': r'^AIza[0-9A-Za-z-_]{35}$',
    },
    'PEXELS_API_KEY': {
        'REQUIRED': False,
        'MIN_LENGTH': 40,
        'PATTERN': r'^[0-9A-Za-z]{40,}$',
    }
}

# Database Security
DATABASES['default'].update({
    'OPTIONS': {
        'sslmode': 'require',
        'connect_timeout': 10,
        'application_name': 'mealprep_api',
    },
    'CONN_MAX_AGE': 600,  # Connection pooling
})

# Logging Security
LOGGING_SECURITY = {
    'SANITIZE_LOGS': True,
    'REDACT_PATTERNS': [
        r'password["\']?\s*:\s*["\']?[^"\'\s,}]+',
        r'token["\']?\s*:\s*["\']?[^"\'\s,}]+',
        r'key["\']?\s*:\s*["\']?[^"\'\s,}]+',
        r'secret["\']?\s*:\s*["\']?[^"\'\s,}]+',
    ],
    'MAX_LOG_SIZE': 100 * 1024 * 1024,  # 100MB
    'BACKUP_COUNT': 5,
}

# Enhanced CORS Settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:9002", 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:9002",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Never allow all origins in production
CORS_ALLOWED_ORIGIN_REGEXES = []  # Be specific about allowed origins

# Security Headers Configuration
SECURITY_HEADERS = {
    'Content-Security-Policy': (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://images.pexels.com; "
        "font-src 'self' https:; "
        "connect-src 'self' https://api.pexels.com https://generativelanguage.googleapis.com; "
        "frame-ancestors 'none';"
    ),
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': (
        'geolocation=(), '
        'microphone=(), '
        'camera=(), '
        'payment=(), '
        'usb=()'
    ),
}

# Environment-specific security
if os.environ.get('DJANGO_ENV') == 'production':
    # Production-only security settings
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_TLS = True
    
    # Stricter session settings for production
    SESSION_COOKIE_AGE = 1800  # 30 minutes
    
    # Enhanced logging for production
    LOGGING['handlers']['security'] = {
        'level': 'WARNING',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': BASE_DIR / 'logs' / 'security.log',
        'maxBytes': LOGGING_SECURITY['MAX_LOG_SIZE'],
        'backupCount': LOGGING_SECURITY['BACKUP_COUNT'],
        'formatter': 'verbose',
    }
    
    LOGGING['loggers']['security'] = {
        'handlers': ['security'],
        'level': 'WARNING',
        'propagate': False,
    }

# Audit Configuration
AUDIT_SETTINGS = {
    'ENABLED': True,
    'LOG_FAILED_LOGINS': True,
    'LOG_PASSWORD_CHANGES': True,
    'LOG_PERMISSION_CHANGES': True,
    'LOG_API_KEY_USAGE': True,
    'RETENTION_DAYS': 90,
}

# Monitoring Configuration
MONITORING = {
    'HEALTH_CHECK_ENABLED': True,
    'METRICS_ENABLED': True,
    'ERROR_TRACKING_ENABLED': True,
    'PERFORMANCE_MONITORING': True,
}