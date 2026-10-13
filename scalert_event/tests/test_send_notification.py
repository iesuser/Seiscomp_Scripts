import json

import pytest

from automate_events import Audience
from send_notification.ies_mail_sender import send_event_mail
from send_notification.message import build_body, build_subject
from send_notification.recipients import RecipientsError, recipient_emails


@pytest.fixture
def recipients_file(tmp_path):
    path = tmp_path / "recipients.json"
    path.write_text(json.dumps([
        {"email": "staff@x.ge", "is_staff": True},
        {"email": "ext@x.ge"},
        {"email": "off@x.ge", "is_staff": True, "is_active": False},
        {"email": "staff@x.ge", "is_staff": True},
    ]))
    return path


class FakeMailer:
    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def send_mail(self, emails, subject, message, **kwargs):
        self.calls.append((emails, subject, message, kwargs))
        return self.result


def test_all_gets_every_active_address(recipients_file):
    assert recipient_emails(Audience.ALL, recipients_file) == ["ext@x.ge", "staff@x.ge"]


def test_staff_gets_only_active_staff(recipients_file):
    assert recipient_emails(Audience.STAFF, recipients_file) == ["staff@x.ge"]


def test_missing_recipients_file(tmp_path):
    with pytest.raises(RecipientsError):
        recipient_emails(Audience.ALL, tmp_path / "missing.json")


def test_subject(make_assessment):
    assert build_subject(make_assessment()) == "Earthquake - Automatic: 2026-10-07 09:15:03. mag=3.2ML"


def test_staff_body_starts_with_staff_only(make_assessment):
    body = build_body(make_assessment(Audience.STAFF), 41.6071, 43.5676)
    lines = body.splitlines()
    assert lines[0] == "STAFF ONLY."
    assert lines[1] == "Automatic: 2026-10-07 09:15:03. mag=3.2ML. საქართველო. ქალაქი გორი:5კმ."
    assert lines[2] == "https://www.google.com/maps/place/41.61,43.57"


def test_all_body_has_no_staff_line(make_assessment):
    assert not build_body(make_assessment(Audience.ALL), 41.6, 43.5).startswith("STAFF ONLY.")


def test_send_hides_recipients(recipients_file, make_assessment):
    mailer = FakeMailer()
    assert send_event_mail(make_assessment(), 41.6, 43.5, mailer=mailer, recipients_file=recipients_file)
    emails, subject, _, kwargs = mailer.calls[0]
    assert emails == ["ext@x.ge", "staff@x.ge"]
    assert kwargs["hide_recipients"] is True


def test_dry_run_sends_nothing(recipients_file, make_assessment):
    mailer = FakeMailer()
    assert not send_event_mail(
        make_assessment(), 41.6, 43.5, mailer=mailer, recipients_file=recipients_file, dry_run=True
    )
    assert mailer.calls == []


def test_smtp_failure_returns_false(recipients_file, make_assessment):
    assert not send_event_mail(
        make_assessment(), 41.6, 43.5, mailer=FakeMailer(result=False), recipients_file=recipients_file
    )
