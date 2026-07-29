"""
Django settings for onesolai project — Production-ready with Render, Supabase, Cloudinary, Resend.
"""

from pathlib import Path
import os
import dj_database_url

# ─────────────────────────────────────────────────────────────────────────────
# Core Paths
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────────────────────────────────────
# Security
# ─────────────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-acfd7!cbf901$vggt81l17o%(#7pd5^txexbbu1q!siy*c(zy_')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS_ENV = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_ENV.split(',')]

CSRF_TRUSTED_ORIGINS_ENV = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in CSRF_TRUSTED_ORIGINS_ENV.split(',')]


# ─────────────────────────────────────────────────────────────────────────────
# Application definition
# ─────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "cloudinary_storage",
    "cloudinary",
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "core",
    "products",
    "orders",
    "notifications",
    "vendors",
    "analytics",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ← Serve static files efficiently
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "onesolai.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.unread_notifications",
                "core.context_processors.site_settings",
                "core.context_processors.currency_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "onesolai.wsgi.application"


# ─────────────────────────────────────────────────────────────────────────────
# Database — Supabase PostgreSQL in production, SQLite locally
# ─────────────────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=0,           # Must be 0 for PgBouncer transaction pooler
            conn_health_checks=True,
        )
    }
    # Force SSL for Supabase
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS']['sslmode'] = 'require'
else:
    # Local development: SQLite
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Static & Media Storage — Cloudinary for Media, WhiteNoise for Static
# ─────────────────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_CLOUDINARY = 'cloudinary://127128733577438:v0mJx8v2FIPRwqsvTTjI_hcrxkM@obgie1pr'
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL', '').strip() or DEFAULT_CLOUDINARY

if CLOUDINARY_URL:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api

    cloudinary.config(
        cloudinary_url=CLOUDINARY_URL
    )

    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = f'https://res.cloudinary.com/{cloudinary.config().cloud_name}/image/upload/'
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'


# ─────────────────────────────────────────────────────────────────────────────
# Password validation
# ─────────────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ─────────────────────────────────────────────────────────────────────────────
# Internationalization
# ─────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ─────────────────────────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────────────────────────
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]


# ─────────────────────────────────────────────────────────────────────────────
# Email — Resend in production, Console locally
# ─────────────────────────────────────────────────────────────────────────────
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')

if RESEND_API_KEY:
    EMAIL_BACKEND = 'onesolai.email_backend.ResendEmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'OneSol AI Hub <noreply@onesolai.com>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL


# ─────────────────────────────────────────────────────────────────────────────
# Payment Gateways
# ─────────────────────────────────────────────────────────────────────────────
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY', 'pk_test_xxxx')
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY', 'sk_test_xxxx')
PAYSTACK_CALLBACK_URL = os.environ.get('PAYSTACK_CALLBACK_URL', 'http://127.0.0.1:8000/payments/paystack/callback/')

FLUTTERWAVE_PUBLIC_KEY = os.environ.get('FLW_PUBLIC_KEY', 'FLWPUBK_TEST-xxxx')
FLUTTERWAVE_SECRET_KEY = os.environ.get('FLW_SECRET_KEY', 'FLWSECK_TEST-xxxx')
FLUTTERWAVE_ENCRYPTION_KEY = os.environ.get('FLW_ENCRYPTION_KEY', '')
FLUTTERWAVE_CALLBACK_URL = os.environ.get('FLW_CALLBACK_URL', 'http://127.0.0.1:8000/payments/flutterwave/callback/')


# ─────────────────────────────────────────────────────────────────────────────
# Currency
# ─────────────────────────────────────────────────────────────────────────────
BASE_CURRENCY = 'NGN'

CURRENCY_RATES_FALLBACK = {
    'NGN': 1,
    'GHS': 0.044,
    'KES': 0.12,
    'ZAR': 0.021,
    'UGX': 43.5,
    'TZS': 29.8,
    'RWF': 15.4,
    'XOF': 6.5,
    'XAF': 6.5,
    'ZMW': 0.26,
    'MWK': 19.8,
    'MUR': 0.52,
    'EGP': 0.35,
    'ETB': 13.2,
    'USD': 0.00063,
    'GBP': 0.00050,
    'EUR': 0.00058,
}

CURRENCY_SYMBOLS = {
    'NGN': '₦', 'GHS': 'GH₵', 'KES': 'KSh', 'ZAR': 'R',
    'UGX': 'USh', 'TZS': 'TSh', 'RWF': 'FRw', 'XOF': 'CFA',
    'XAF': 'CFA', 'ZMW': 'K', 'MWK': 'MK', 'MUR': '₨',
    'EGP': 'E£', 'ETB': 'Br', 'USD': '$', 'GBP': '£', 'EUR': '€',
}


# ─────────────────────────────────────────────────────────────────────────────
# Reverse Proxy / HTTPS (Render uses forwarded headers)
# ─────────────────────────────────────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Production security settings (only enabled when DEBUG=False)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# ─────────────────────────────────────────────────────────────────────────────
# Jazzmin Admin Theme
# ─────────────────────────────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    "site_title": "OneSol AI Hub Admin",
    "site_header": "OneSol AI Hub",
    "site_brand": "",
    "site_logo": "assets/logo.png",
    "welcome_sign": "Welcome to OneSol AI Hub Administration",
    "copyright": "OneSol AI Hub Ltd",
    "show_ui_builder": False,
    "custom_css": "css/admin_jazzmin_custom.css",
    "custom_js": "js/admin_jazzmin_custom.js",
    "topmenu_links": [
        {"name": "Home",  "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Frontend", "url": "home", "new_window": False},
        {"name": "Admin Analytics", "url": "analytics:dashboard", "new_window": False},
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "accounts.User": "fas fa-user-shield",
        "accounts.Profile": "fas fa-id-badge",
        "products.Category": "fas fa-tags",
        "products.Tool": "fas fa-layer-group",
        "vendors.Vendor": "fas fa-plug",
        "vendors.VendorBalance": "fas fa-wallet",
        "orders.Order": "fas fa-cart-shopping",
        "orders.PaymentTransaction": "fas fa-money-bill-transfer",
        "orders.OrderAPIRequest": "fas fa-server",
        "core.SiteSettings": "fas fa-gear",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
}

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "navbar": "navbar-dark",
    "navbar_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "no_navbar_border": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "button_classes": {
        "primary": "btn-outline-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
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
        'products.tools': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
