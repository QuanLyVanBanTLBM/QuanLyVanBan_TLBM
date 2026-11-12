"""Run Group 3 against the shared release without migrating other groups.

Uses real, checked-in staging Employee/RBAC and Group 3 sources. This optional
profile is for local Group 3 validation. The full staging settings remain the
integration target for the deployment owner.
"""
from .settings import *  # noqa: F403,F401

INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "corsheaders",
    "rest_framework", "rest_framework_simplejwt", "rest_framework_simplejwt.token_blacklist",
    "accounts", "organizations", "authorization", "records",
]
ROOT_URLCONF = "config.records_release_urls"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.getenv("DB_NAME", ""),  # noqa: F405
    "USER": os.getenv("DB_USER", "postgres"),  # noqa: F405
    "PASSWORD": os.getenv("DB_PASSWORD", ""),  # noqa: F405
    "HOST": os.getenv("DB_HOST", "127.0.0.1"),  # noqa: F405
    "PORT": os.getenv("DB_PORT", "5432"),  # noqa: F405
    "OPTIONS": {"connect_timeout": 5},
}}
if not DATABASES["default"]["NAME"]:
    raise RuntimeError("DB_NAME is required for the PostgreSQL records release profile")
# Records implements its filters explicitly; the focused profile does not
# require django-filter from the other staged modules.
REST_FRAMEWORK = dict(REST_FRAMEWORK)  # noqa: F405
REST_FRAMEWORK["DEFAULT_FILTER_BACKENDS"] = []
