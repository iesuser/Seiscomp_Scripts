import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "recipients"))

import update_recipients  # noqa: E402
from automate_events import Audience  # noqa: E402
from config import RecipientsApiSettings  # noqa: E402
from send_notification.recipients import recipient_emails  # noqa: E402
from update_recipients import (  # noqa: E402
    RecipientsApiError,
    recips_url,
    to_email_recipients,
    to_sms_recipients,
)

API_ITEMS = [
    {
        "id": 1, "username": "Roma", "is_staff": True, "is_active": True,
        "emails": [
            {"email": "roma@iliauni.edu.ge", "is_active": True},
            {"email": "old@iliauni.edu.ge", "is_active": False},
        ],
        "numbers": [{"phone_number": "+995", "is_active": True}],
    },
    {
        "id": 2, "username": "External", "is_staff": False, "is_active": True,
        "emails": [{"email": "ext@example.com", "is_active": True}],
        "numbers": [{"phone_number": "+995222", "is_active": False}],
    },
    {
        "id": 3, "username": "Disabled", "is_staff": True, "is_active": False,
        "emails": [{"email": "off@iliauni.edu.ge", "is_active": True}],
    },
]


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def api(tmp_path):
    return RecipientsApiSettings("https://example.test:3030/", "key", None, 5)


@pytest.fixture
def fake_api(monkeypatch):
    """Make urlopen return `payload`; records the requests made."""
    requests = []

    def install(payload):
        def urlopen(request, timeout, context):
            requests.append(request)
            return FakeResponse(json.dumps(payload).encode())

        monkeypatch.setattr(update_recipients.urllib.request, "urlopen", urlopen)
        return requests

    return install


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Point both recipient files into tmp_path; returns (email_file, sms_file)."""
    email_file = tmp_path / "email_recipients.json"
    sms_file = tmp_path / "sms_recipients.json"
    monkeypatch.setenv("RECIPIENTS_FILE", str(email_file))
    monkeypatch.setenv("SMS_RECIPIENTS_FILE", str(sms_file))
    monkeypatch.setenv("Recp_Exporter_API_URL", "https://example.test:3030/")
    monkeypatch.setenv("Recp_Exporter_API_KEY", "key")
    monkeypatch.setattr(update_recipients, "LOG_FILE", tmp_path / "update.log")
    return email_file, sms_file


def test_url_from_root_or_endpoint():
    assert recips_url("https://x:3030/") == "https://x:3030/api/recips/"
    assert recips_url("https://x:3030") == "https://x:3030/api/recips/"
    assert recips_url("http://127.0.0.1:5000/api/recips/") == "http://127.0.0.1:5000/api/recips/"


def test_conversion_combines_recipient_and_email_activity():
    entries = {e["email"]: e for e in to_email_recipients(API_ITEMS)}
    assert entries["roma@iliauni.edu.ge"] == {
        "username": "Roma", "email": "roma@iliauni.edu.ge", "is_staff": True, "is_active": True,
    }
    assert entries["old@iliauni.edu.ge"]["is_active"] is False
    assert entries["off@iliauni.edu.ge"]["is_active"] is False
    assert entries["ext@example.com"]["is_staff"] is False


def test_sms_conversion():
    entries = {e["phone_number"]: e for e in to_sms_recipients(API_ITEMS)}
    assert entries["+995"] == {"username": "Roma", "phone_number": "+995", "is_staff": True, "is_active": True}
    assert entries["+995222"]["is_active"] is False
    assert len(entries) == 2


def test_converted_file_is_read_by_sender(tmp_path):
    path = tmp_path / "email_recipients.json"
    path.write_text(json.dumps(to_email_recipients(API_ITEMS)))
    assert recipient_emails(Audience.STAFF, path) == ["roma@iliauni.edu.ge"]
    assert recipient_emails(Audience.ALL, path) == ["ext@example.com", "roma@iliauni.edu.ge"]


def test_fetch_sends_api_key(api, fake_api):
    requests = fake_api({"items": API_ITEMS, "total": 3})
    assert len(update_recipients.fetch_recips(api)) == 3
    assert requests[0].full_url == "https://example.test:3030/api/recips/"
    assert requests[0].get_header("X-api-key") == "key"


def test_fetch_rejects_unexpected_json(api, fake_api):
    fake_api({"error": "nope"})
    with pytest.raises(RecipientsApiError):
        update_recipients.fetch_recips(api)


def test_fetch_requires_key(api):
    with pytest.raises(RecipientsApiError):
        update_recipients.fetch_recips(RecipientsApiSettings(api.base_url, "", api.ca_file, 5))


def test_main_writes_both_files(env, fake_api):
    email_file, sms_file = env
    fake_api({"items": API_ITEMS, "total": 3})
    assert update_recipients.main([]) == update_recipients.EXIT_OK
    assert len(json.loads(email_file.read_text())) == 4
    assert len(json.loads(sms_file.read_text())) == 2


def test_main_keeps_previous_files_when_api_returns_nobody(env, fake_api):
    for path in env:
        path.write_text("previous")
    fake_api({"items": [], "total": 0})
    assert update_recipients.main([]) == update_recipients.EXIT_FAILED
    assert all(path.read_text() == "previous" for path in env)


def test_empty_sms_list_does_not_block_email_update(env, fake_api):
    email_file, sms_file = env
    sms_file.write_text("previous")
    items = [{**item, "numbers": []} for item in API_ITEMS]
    fake_api({"items": items, "total": 3})
    assert update_recipients.main([]) == update_recipients.EXIT_FAILED
    assert len(json.loads(email_file.read_text())) == 4
    assert sms_file.read_text() == "previous"


def test_main_keeps_previous_files_when_api_fails(env, monkeypatch):
    for path in env:
        path.write_text("previous")

    def broken(*args, **kwargs):
        raise update_recipients.urllib.error.URLError("down")

    monkeypatch.setattr(update_recipients.urllib.request, "urlopen", broken)
    assert update_recipients.main([]) == update_recipients.EXIT_FAILED
    assert all(path.read_text() == "previous" for path in env)


def test_dry_run_writes_nothing(env, fake_api):
    fake_api({"items": API_ITEMS, "total": 3})
    assert update_recipients.main(["--dry-run"]) == update_recipients.EXIT_OK
    assert not any(path.exists() for path in env)
