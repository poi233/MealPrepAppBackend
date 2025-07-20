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
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
CORS_ALLOW_CREDENTIALS = True

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

# Cache for production (use dummy cache for Vercel, Redis for other deployments)
REDIS_URL = config('REDIS_URL', default='')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

# Rate limiting
RATELIMIT_ENABLE = True