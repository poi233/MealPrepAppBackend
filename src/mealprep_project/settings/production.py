"""
Production settings for MealPrepAI Django backend.
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# Vercel deployment settings
ALLOWED_HOSTS = ['*']  # Vercel handles this
VERCEL_URL = config('VERCEL_URL', default='')
if VERCEL_URL:
    ALLOWED_HOSTS = [VERCEL_URL, '.vercel.app']

# Security settings for production (adjusted for Vercel)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
# Disable HSTS and SSL redirect for Vercel (handled by platform)
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'

# Production CORS settings
cors_origins = config('CORS_ALLOWED_ORIGINS', default='').split(',')
# Filter out empty strings
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins if origin.strip()]

# If no CORS origins are configured, allow common Vercel patterns
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        "https://mealsuggestpoi.zapto.org",
        "https://meal-prep-pubbzexdt-pois-projects-1cbc0dc1.vercel.app",
        "https://meal-prep-ai-git-master-pois-projects-1cbc0dc1.vercel.app",
    ]

# Also allow all Vercel app domains for this project
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://meal-prep-.*\.vercel\.app$",
    r"^https://.*-pois-projects-1cbc0dc1\.vercel\.app$",
    r"^https://mealsuggestpoi\.zapto\.org$",
]

# Additional CORS settings for production
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_ALLOWED_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Database connection pooling for production
DATABASES['default'].update({
    'CONN_MAX_AGE': 60,
    'OPTIONS': {
        'sslmode': 'require',
        'connect_timeout': 10,
    },
})

# Email backend for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Production logging - Console only for Vercel (read-only filesystem)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'mealprep_project': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Static files handling with WhiteNoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Cache for production (use dummy cache for Vercel)
# Vercel doesn't support persistent Redis, so we use dummy cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Rate limiting
RATELIMIT_ENABLE = True