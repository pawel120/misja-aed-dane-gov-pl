"""
Logowanie jury do panelu jednym kliknięciem, tylko w środowisku demo
(włączane w ``mcod/settings/aed_demo.py``, nie w ustawieniach portalu).

Link ``/aed-demo/wejdz/<kod>/`` loguje na konto jury i otwiera panel. Kod jest
tajny i nie ma go w repozytorium: zmienna ``AED_DEMO_LOGIN_TOKEN`` albo plik
``data/aed/demo_login_token.txt`` (w ``.gitignore``). Bez kodu, z błędnym kodem
albo po terminie ``AED_DEMO_LOGIN_UNTIL`` adres odpowiada 404.
"""

import datetime
import logging
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.http import Http404, HttpResponseRedirect
from django.utils import timezone
from django.utils.crypto import constant_time_compare

logger = logging.getLogger("mcod")

AED_DEMO_LOGIN_PREFIX = "/aed-demo/wejdz/"
AED_DEMO_LOGIN_BACKEND = "django.contrib.auth.backends.ModelBackend"


def get_aed_demo_login_token() -> str:
    token = getattr(settings, "AED_DEMO_LOGIN_TOKEN", "") or ""
    if token:
        return token.strip()
    path = getattr(settings, "AED_DEMO_LOGIN_TOKEN_FILE", "")
    if path and Path(path).is_file():
        return Path(path).read_text(encoding="utf-8").strip()
    return ""


def get_aed_demo_login_deadline() -> Optional[datetime.datetime]:
    value = getattr(settings, "AED_DEMO_LOGIN_UNTIL", "")
    if not value:
        return None
    return datetime.datetime.fromisoformat(value)


class AEDDemoJuryLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(AED_DEMO_LOGIN_PREFIX):
            return self.login_jury(request)
        return self.get_response(request)

    def login_jury(self, request):
        expected = get_aed_demo_login_token()
        given = request.path[len(AED_DEMO_LOGIN_PREFIX) :].strip("/")
        deadline = get_aed_demo_login_deadline()
        if not expected or not given or not constant_time_compare(given, expected):
            raise Http404
        if deadline is not None and timezone.now() > deadline:
            raise Http404
        user = get_user_model().objects.filter(email=settings.AED_DEMO_LOGIN_EMAIL, is_active=True, is_staff=True).first()
        if user is None:
            logger.warning("AED demo login: no active staff account %s.", settings.AED_DEMO_LOGIN_EMAIL)
            raise Http404
        login(request, user, backend=AED_DEMO_LOGIN_BACKEND)
        logger.info("AED demo login used for %s.", user.email)
        return HttpResponseRedirect(getattr(settings, "AED_DEMO_LOGIN_NEXT", "/") or "/")
