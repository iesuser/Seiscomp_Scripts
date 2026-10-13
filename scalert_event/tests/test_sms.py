import json
from dataclasses import replace

import pytest

from automate_events import Audience
from config import load_settings
from send_notification.ies_sms_sender import SmsSender, send_event_sms
from send_notification.message import build_sms_text
from send_notification.recipients import normalize_phone, recipient_numbers


@pytest.fixture
def numbers_file(tmp_path):
    path = tmp_path / "sms_recipients.json"
    path.write_text(json.dumps([
        {"phone_number": "+995 555 11-11-11", "is_staff": True},
        {"phone_number": "555222222"},
        {"phone_number": "+995555333333", "is_staff": True, "is_active": False},
        {"phone_number": "12345"},
        {"phone_number": "995555111111", "is_staff": True},
    ]))
    return path


@pytest.fixture
def sms_settings():
    return replace(
        load_settings().sms,
        providers=("magti", "smsoffice", "gsm"),
        magti_username="u", magti_password="p",
        smsoffice_key="k", smsoffice_balance_warning=100,
        gsm_url="http://gsm/send.php", gsm_code="c",
    )


class FakeHttp:
    """Answers by URL: each value is a function (method, params, data) -> (status, body)."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, method, url, *, params=None, data=None, timeout):
        self.calls.append((url, params or {}, data or {}))
        for prefix, answer in self.routes.items():
            if url.startswith(prefix):
                return answer(method, params or {}, data or {})
        raise OSError(f"no route for {url}")


def make_sender(settings, routes):
    http = FakeHttp(routes)
    return SmsSender(settings, http=http, sleep=lambda s: None), http


def magti_ok(method, params, data):
    if "message_id" in params:
        return 200, "1"
    return 200, f"0000 - id{params['to']}"


def balance(method, params, data):
    return 200, "5000"


def test_numbers_are_normalized():
    assert normalize_phone("+995 555 12-34-56") == "995555123456"
    assert normalize_phone("555123456") == "995555123456"
    assert normalize_phone("00995555123456") == "995555123456"
    assert normalize_phone("12345") is None


def test_all_gets_every_active_number(numbers_file):
    assert recipient_numbers(Audience.ALL, numbers_file) == ["995555111111", "995555222222"]


def test_staff_gets_only_active_staff_numbers(numbers_file):
    assert recipient_numbers(Audience.STAFF, numbers_file) == ["995555111111"]


def test_sms_text(make_assessment):
    assert build_sms_text(make_assessment(Audience.ALL)) == (
        "Automatic: 2026-10-07 09:15:03. mag=3.2ML. საქართველო. ქალაქი გორი:5კმ."
    )
    assert build_sms_text(make_assessment(Audience.STAFF)).startswith("STAFF ONLY.\nAutomatic: ")


def test_magti_delivers_everything(sms_settings):
    sender, http = make_sender(sms_settings, {sms_settings.magti_url: magti_ok,
                                              sms_settings.magti_track_url: magti_ok,
                                              sms_settings.smsoffice_balance_url: balance})
    assert sender.send("hi", ["995555111111", "995555222222"]) == []
    assert not any(url.startswith(sms_settings.smsoffice_url) for url, _, _ in http.calls)


def test_unconfirmed_magti_falls_back_to_smsoffice(sms_settings):
    def magti_track(method, params, data):
        return 200, "1" if params["message_id"] == "id995555111111" else "2"

    sender, http = make_sender(sms_settings, {
        sms_settings.magti_track_url: magti_track,
        sms_settings.magti_url: magti_ok,
        sms_settings.smsoffice_balance_url: balance,
        sms_settings.smsoffice_url: lambda m, p, d: (200, json.dumps({"Success": True, "ErrorCode": 0})),
    })
    assert sender.send("hi", ["995555111111", "995555222222"]) == []
    office = [p["destination"] for url, p, _ in http.calls
              if url.startswith(sms_settings.smsoffice_url) and "destination" in p]
    assert office == ["995555222222"]


def test_gsm_is_last_resort(sms_settings):
    sender, http = make_sender(sms_settings, {
        sms_settings.magti_track_url: magti_ok,
        sms_settings.magti_url: lambda m, p, d: (200, "0001"),
        sms_settings.smsoffice_balance_url: balance,
        sms_settings.smsoffice_url: lambda m, p, d: (200, json.dumps({"Success": False, "ErrorCode": 20})),
        sms_settings.gsm_url: lambda m, p, d: (200, "ok"),
    })
    assert sender.send("hi", ["995555111111", "995555222222"]) == []
    gsm = [d for url, _, d in http.calls if url.startswith(sms_settings.gsm_url)]
    assert gsm == [{"code": "c", "message": "hi", "numbers": "995555111111,995555222222"}]
    office = [url for url, p, _ in http.calls if url.startswith(sms_settings.smsoffice_url)]
    assert len(office) == 2 * 3


def test_everything_down_returns_failed_numbers(sms_settings):
    sender, _ = make_sender(sms_settings, {})
    assert sender.send("hi", ["995555111111"]) == ["995555111111"]


def test_unconfigured_provider_is_skipped(sms_settings):
    settings = replace(sms_settings, magti_password="", smsoffice_key="")
    sender, http = make_sender(settings, {settings.gsm_url: lambda m, p, d: (200, "ok")})
    assert sender.send("hi", ["995555111111"]) == []
    assert [url for url, _, _ in http.calls] == [settings.gsm_url]


def test_low_balance_is_logged(sms_settings, caplog):
    sender, _ = make_sender(sms_settings, {sms_settings.smsoffice_balance_url: lambda m, p, d: (200, "42")})
    assert sender.check_smsoffice_balance() == 42
    assert "SMS BALANCE LOW" in caplog.text


class FakeSender:
    def __init__(self, failed=()):
        self.failed = list(failed)
        self.calls = []

    def send(self, message, numbers):
        self.calls.append((message, numbers))
        return self.failed


def test_send_event_sms_to_staff(numbers_file, make_assessment):
    sender = FakeSender()
    assert send_event_sms(make_assessment(Audience.STAFF), sender=sender, recipients_file=numbers_file)
    message, numbers = sender.calls[0]
    assert numbers == ["995555111111"]
    assert message.startswith("STAFF ONLY.\n")


def test_send_event_sms_dry_run(numbers_file, make_assessment):
    sender = FakeSender()
    assert not send_event_sms(make_assessment(), sender=sender, recipients_file=numbers_file, dry_run=True)
    assert sender.calls == []


def test_send_event_sms_reports_failed_numbers(numbers_file, make_assessment, caplog):
    sender = FakeSender(failed=["995555222222"])
    assert not send_event_sms(make_assessment(), sender=sender, recipients_file=numbers_file)
    assert "SMS FAILED" in caplog.text and "995555222222" in caplog.text
