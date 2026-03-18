from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'unsafe-secret-key')

DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = (
    ['*']
    if DEBUG
    else os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
)

# ---------------------------------------------------------------------------
# CORS / CSRF
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv('DJANGO_CORS_ALLOWED_ORIGINS', '').split(',')
    if o.strip()
]

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # internal
    'stocknlp',
    'tickers',
    'signals',
    'scraper.apps.ScraperConfig',
    # third-party
    'django_rq',
    'rest_framework',
    'django_filters',
    'corsheaders',
    'django_extensions',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    *([] if DEBUG else ['django.middleware.csrf.CsrfViewMiddleware']),
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'stocknlp.urls'
WSGI_APPLICATION = 'stocknlp.wsgi.application'

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': os.getenv('POSTGRES_PORT'),
    },
}

# ---------------------------------------------------------------------------
# Redis / RQ
# ---------------------------------------------------------------------------

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

_RQ_BASE = {
    'HOST': REDIS_HOST,
    'PORT': REDIS_PORT,
    'DB': 0,
    'DEFAULT_TIMEOUT': 360,
}

RQ_QUEUES = {
    'scraper_queue': _RQ_BASE,
    'user_queue': _RQ_BASE,
}

# ---------------------------------------------------------------------------
# Cache (django-redis)
# ---------------------------------------------------------------------------

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/1',   # DB 1 — separate from RQ (DB 0)
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'stocknlp',
        'TIMEOUT': 300,  # default 5 min; individual cache.set() calls override this
    }
}

# ---------------------------------------------------------------------------
# Cache TTLs (seconds) — tune here, applied everywhere automatically
# ---------------------------------------------------------------------------

CACHE_TTL_STOCK_DATA    = int(os.getenv('CACHE_TTL_STOCK_DATA',    60 * 60))   # 1 hour
CACHE_TTL_PREDICTIONS   = int(os.getenv('CACHE_TTL_PREDICTIONS',   60 * 10))   # 10 minutes
CACHE_TTL_WORKER_RESULT = int(os.getenv('CACHE_TTL_WORKER_RESULT', 60 * 5))    # 5 minutes

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = '/static/'

# ---------------------------------------------------------------------------
# Auth / password validators
# ---------------------------------------------------------------------------

_AUTH_BASE = 'django.contrib.auth.password_validation'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': f'{_AUTH_BASE}.UserAttributeSimilarityValidator'},
    {'NAME': f'{_AUTH_BASE}.MinimumLengthValidator'},
    {'NAME': f'{_AUTH_BASE}.CommonPasswordValidator'},
    {'NAME': f'{_AUTH_BASE}.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Primary key
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# ML model paths
# ---------------------------------------------------------------------------

MODEL_WEIGHTS_PATH   = BASE_DIR / 'models' / 'best_model.pth'
MODEL_PARAMS_PATH    = BASE_DIR / 'models' / 'params' / 'best_params.json'
WORD_TO_INDEX_PATH   = BASE_DIR / 'models' / 'word_to_index.json'
TICKER_TO_INDEX_PATH = BASE_DIR / 'models' / 'ticker_to_index.json'

DEFAULT_MODEL = 'transformer_finbert'

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny' if DEBUG else 'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        []
        if DEBUG
        else [
            'rest_framework.authentication.SessionAuthentication',
            'rest_framework.authentication.BasicAuthentication',
        ]
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'signals.views': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'httpcore': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'httpx': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        '': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
        },
    },
}

# ---------------------------------------------------------------------------
# Security hardening (production only)
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = os.getenv('DJANGO_SSL_REDIRECT', 'False').lower() in ('1', 'true', 'yes')
if not DEBUG:
    
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'