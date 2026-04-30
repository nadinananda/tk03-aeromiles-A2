from aeromiles.settings import *


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
