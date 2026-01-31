"""
Production settings for edupane_backend project.
"""

import os
from .settings import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)

# Update allowed hosts for Azure
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.azurewebsites.net',
    '.azure.com',
    'edupane-backend.onrender.com',
]

# Add your Azure app service domain here
# if os.environ.get('WEBSITE_HOSTNAME'):
#     ALLOWED_HOSTS.append(os.environ.get('WEBSITE_HOSTNAME'))

# CORS settings for production
CORS_ALLOWED_ORIGINS = [
    "https://edupane-python-webapp.azurewebsites.net",
    "https://edupane-python-webapp.azure.com",
    "https://edupane-backend.onrender.com",
]

# Add your frontend domain here
# if os.environ.get('FRONTEND_URL'):
#     CORS_ALLOWED_ORIGINS.append(os.environ.get('FRONTEND_URL'))

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Add whitenoise for static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Configure whitenoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Additional static files directories
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'staticfiles'),
]

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Database configuration for Azure
# if os.environ.get('DATABASE_URL'):
#     import dj_database_url
#     DATABASES = {
#         'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
#     }

# Redis configuration for Azure
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("edupane.redis.cache.windows.net", 6380)],
        },
    },
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Celery Configuration
CELERY_BROKER_URL = 'redis://edupane.redis.cache.windows.net/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
