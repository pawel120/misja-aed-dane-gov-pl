# Ustawienia demo wykazu AED (HackNation 2026): lokalne ustawienia portalu dostępne pod 127.0.0.1.
from mcod.settings.base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG  # noqa: F405
INTERNAL_IPS = (
    "127.0.0.1",
    "localhost",
    "172.18.18.100",
)  # needed to use debug processor in django templates


if EMAIL_HOST:  # noqa: F405
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
else:
    EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
    EMAIL_FILE_PATH = "/tmp/app-messages"

NO_REPLY_EMAIL = "no-reply@mcod.local"

ELASTICSEARCH_DSL_INDEX_SETTINGS = {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "timeout": 1,
}

ELASTICSEARCH_HISTORIES_IDX_SETTINGS = {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "timeout": 1,
}

CELERY_TASK_ALWAYS_EAGER = False

FIXTURE_DIRS = [
    str(ROOT_DIR("test-data/fixtures")),
]

MEDIA_ROOT = str(ROOT_DIR("media"))
ACADEMY_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "academy"))
IMAGES_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "images"))
LABORATORY_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "lab_reports"))
MEETINGS_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "meetings"))
NEWSLETTER_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "newsletter"))
RESOURCES_FILES_TO_REMOVE_ROOT = str(
    ROOT_DIR.path(MEDIA_ROOT, "to_be_removed", "resources")
)
RESOURCES_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "resources"))
SHOWCASES_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "showcases"))

SESSION_COOKIE_NAME = "local_sessionid"
SESSION_COOKIE_DOMAIN = None  # demo na 127.0.0.1, bez domeny mcod.local
SESSION_COOKIE_SECURE = False
API_TOKEN_COOKIE_NAME = "local_apiauthtoken"


LOGGING["loggers"]["django.db.backends"]["level"] = "ERROR"
LOGGING["loggers"]["django.db.backends"]["handlers"] = ["console"]
LOGGING["loggers"]["django.request"]["level"] = "DEBUG"
LOGGING["loggers"]["django.request"]["handlers"] = ["console"]
LOGGING["loggers"]["django.server"]["level"] = "DEBUG"
LOGGING["loggers"]["django.server"]["handlers"] = ["console"]
LOGGING["loggers"]["signals"]["level"] = "DEBUG"
LOGGING["loggers"]["signals"]["handlers"] = ["signals-console-handler"]
LOGGING["loggers"]["celery.app.trace"]["level"] = "WARNING"
LOGGING["loggers"]["celery.app.trace"]["handlers"] = ["console"]
LOGGING["loggers"]["mcod"]["handlers"] = ["console"]
LOGGING["loggers"]["resource_file_processing"]["handlers"] = ["console"]
LOGGING['loggers']['mcod-api']['level'] = 'DEBUG'

COMPONENT = env("COMPONENT", default="admin")
ENVIRONMENT = "local"

AXES_ENABLED=False

# Demo AED: panel i API pod 127.0.0.1, bez Discourse.
CSRF_COOKIE_DOMAIN = None
DISCOURSE_FORUM_ENABLED = False
ADMIN_URL = env("ADMIN_URL", default="http://127.0.0.1:8001")

# local.py.sample dodaje "timeout" do ustawień indeksu; Elasticsearch 6.8 odrzuca to ustawienie.
ELASTICSEARCH_DSL_INDEX_SETTINGS = {"number_of_shards": 1, "number_of_replicas": 0}
ELASTICSEARCH_HISTORIES_IDX_SETTINGS = {"number_of_shards": 1, "number_of_replicas": 0}


class AEDDemoBannerMiddleware:
    """Pasek na każdej stronie HTML: to kopia demonstracyjna, nie serwis dane.gov.pl."""

    BANNER = (
        '<div style="position:sticky;top:0;z-index:99999;background:#b00020;color:#fff;'
        'font:600 14px/1.4 sans-serif;padding:8px 12px;text-align:center">'
        "Środowisko testowe HackNation 2026 – kopia otwartego kodu portalu z modułem "
        "„Wykaz AED”. To nie jest serwis dane.gov.pl.</div>"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "")
        if "text/html" in content_type and not getattr(response, "streaming", False):
            body = response.content.decode(response.charset or "utf-8", errors="ignore")
            if "<body" in body and "Środowisko testowe HackNation" not in body:
                start = body.index("<body")
                end = body.index(">", start) + 1
                body = body[:end] + self.BANNER + body[end:]
                response.content = body.encode(response.charset or "utf-8")
                if response.has_header("Content-Length"):
                    response["Content-Length"] = str(len(response.content))
        return response


MIDDLEWARE = list(MIDDLEWARE) + ["mcod.settings.aed_demo.AEDDemoBannerMiddleware"]  # noqa: F405
