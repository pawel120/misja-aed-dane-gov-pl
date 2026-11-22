"""Logowanie jury jednym kliknięciem w środowisku demo AED (bez bazy danych)."""

from unittest import mock

import pytest
from django.http import Http404, HttpResponse
from django.test import RequestFactory, override_settings

from mcod.resources.aed_demo_login import (
    AEDDemoJuryLoginMiddleware,
    clear_invalid_last_logged_method,
    get_aed_demo_login_token,
)

TOKEN = "s3kretny-kod-jury"
DEMO = dict(
    AED_DEMO_LOGIN_TOKEN=TOKEN,
    AED_DEMO_LOGIN_TOKEN_FILE="",
    AED_DEMO_LOGIN_EMAIL="jury@aed.demo",
    AED_DEMO_LOGIN_UNTIL="2099-01-01T00:00:00+01:00",
    AED_DEMO_LOGIN_NEXT="/resources/resource/1/change/",
)


def middleware():
    return AEDDemoJuryLoginMiddleware(lambda request: HttpResponse("panel"))


def get(path):
    return RequestFactory().get(path)


@override_settings(**DEMO)
def test_other_paths_are_not_touched():
    assert middleware()(get("/resources/resource/")).content == b"panel"


@override_settings(**DEMO)
@mock.patch("mcod.resources.aed_demo_login.clear_invalid_last_logged_method")
@mock.patch("mcod.resources.aed_demo_login.login")
@mock.patch("mcod.resources.aed_demo_login.get_user_model")
def test_correct_link_logs_jury_in_and_opens_panel(get_user_model, login, clear_login_method):
    jury = mock.Mock(email="jury@aed.demo", last_logged_method=None)
    get_user_model.return_value.objects.filter.return_value.first.return_value = jury
    response = middleware()(get(f"/aed-demo/wejdz/{TOKEN}/"))
    assert response.status_code == 302
    assert response["Location"] == "/resources/resource/1/change/"
    get_user_model.return_value.objects.filter.assert_called_once_with(email="jury@aed.demo", is_active=True, is_staff=True)
    assert login.call_args.args[1] is jury
    clear_login_method.assert_called_once_with(jury)


@pytest.mark.parametrize("path", ["/aed-demo/wejdz/zly-kod/", "/aed-demo/wejdz/", f"/aed-demo/wejdz/{TOKEN}x/"])
@override_settings(**DEMO)
@mock.patch("mcod.resources.aed_demo_login.login")
def test_wrong_or_missing_code_is_404(login, path):
    with pytest.raises(Http404):
        middleware()(get(path))
    login.assert_not_called()


@override_settings(**dict(DEMO, AED_DEMO_LOGIN_TOKEN=""))
@mock.patch("mcod.resources.aed_demo_login.login")
def test_no_code_configured_means_no_login_link(login):
    with pytest.raises(Http404):
        middleware()(get("/aed-demo/wejdz/cokolwiek/"))
    login.assert_not_called()


@override_settings(**dict(DEMO, AED_DEMO_LOGIN_UNTIL="2020-01-01T00:00:00+01:00"))
@mock.patch("mcod.resources.aed_demo_login.login")
def test_expired_link_is_404(login):
    with pytest.raises(Http404):
        middleware()(get(f"/aed-demo/wejdz/{TOKEN}/"))
    login.assert_not_called()


@override_settings(**DEMO)
@mock.patch("mcod.resources.aed_demo_login.login")
@mock.patch("mcod.resources.aed_demo_login.get_user_model")
def test_missing_jury_account_is_404(get_user_model, login):
    get_user_model.return_value.objects.filter.return_value.first.return_value = None
    with pytest.raises(Http404):
        middleware()(get(f"/aed-demo/wejdz/{TOKEN}/"))
    login.assert_not_called()


def test_code_can_come_from_file_outside_git(tmp_path):
    path = tmp_path / "demo_login_token.txt"
    path.write_text(" z-pliku \n", encoding="utf-8")
    with override_settings(AED_DEMO_LOGIN_TOKEN="", AED_DEMO_LOGIN_TOKEN_FILE=str(path)):
        assert get_aed_demo_login_token() == "z-pliku"


class _UserWithLoginMethod:
    """Konto z polem ``last_logged_method`` portalu, bez bazy danych."""

    from mcod.users.models import User as _User

    _meta = _User._meta
    objects = mock.Mock()

    def __init__(self, value):
        self.pk = 7
        self.last_logged_method = value


@pytest.mark.parametrize("value", ["Form", "nieznana-metoda"])
def test_login_method_not_valid_in_polish_panel_is_cleared(value):
    # Na serwerze demo konto jury miało „Form”, a polski panel dopuszcza tłumaczenie tej wartości.
    from django.utils import translation

    with translation.override("pl"):
        user = _UserWithLoginMethod(value)
        clear_invalid_last_logged_method(user)
    assert user.last_logged_method is None
    user.objects.filter.assert_called_with(pk=7)


@pytest.mark.parametrize("value", [None, "WK"])
def test_valid_login_method_is_kept(value):
    user = _UserWithLoginMethod(value)
    user.objects.reset_mock()
    clear_invalid_last_logged_method(user)
    assert user.last_logged_method == value
    user.objects.filter.assert_not_called()
