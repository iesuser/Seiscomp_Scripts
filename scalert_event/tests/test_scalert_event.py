import logging
from dataclasses import replace
from datetime import datetime

import pytest

import scalert_event
from automate_events import Audience
from config import load_settings
from seiscomp_db import EventData, EventNotReady
from send_eq2api.send_eq2api import EventApiError

EVENT = EventData(
    event_id="ies1",
    origin_id="Origin/1",
    origin_time=datetime(2026, 9, 8, 4, 52, 15),
    latitude=41.607,
    longitude=43.5676,
    depth=15.3,
    evaluation_mode="automatic",
    event_type="earthquake",
    magnitudes={"ML": 4.23},
)


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "test.log"))
    return load_settings()


@pytest.fixture
def channels(monkeypatch):
    """Fake mail, SMS and site API; records what each channel was asked to send."""
    sent = {"mail": [], "sms": [], "sms_kwargs": [], "api": [], "published": []}

    def fake_mail(result, lat, lon, **kwargs):
        sent["mail"].append(result)
        return True

    def fake_sms(result, **kwargs):
        sent["sms"].append(result)
        sent["sms_kwargs"].append(kwargs)
        return True

    class FakeEventApiClient:
        def __init__(self, settings):
            pass

        def add_event(self, payload):
            sent["api"].append(payload)
            return {"id": 1, "created": True, "is_published": False}

        def publish_event(self, event_id):
            sent["published"].append(event_id)
            return {"published": True}

    monkeypatch.setattr(scalert_event, "send_event_mail", fake_mail)
    monkeypatch.setattr(scalert_event, "send_event_sms", fake_sms)
    monkeypatch.setattr(scalert_event, "EventApiClient", FakeEventApiClient)
    return sent


@pytest.fixture
def run(monkeypatch, settings, make_assessment, channels):
    """Run `process` with fake database, rules and delivery; returns the mailed assessments."""

    def run_once(event=EVENT, assessment=None, settings=settings):
        assessment = assessment or make_assessment()
        before = len(channels["mail"])
        monkeypatch.setattr(scalert_event, "load_event", lambda *a, **k: event)
        monkeypatch.setattr(scalert_event, "process_event", lambda *a, **k: assessment)
        scalert_event.process("ies1", settings, dry_run=False)
        return channels["mail"][before:]

    return run_once


def test_parse_scalert_arguments():
    args = scalert_event.parse_args(["msg", "1", "ies2026rudf", "12", "4.2"])
    assert (args.event_id, args.flag, args.arrivals, args.magnitude) == ("ies2026rudf", "1", "12", "4.2")


def test_parse_scalert_arguments_without_magnitude():
    args = scalert_event.parse_args(["msg", "0", "ies2026rudf", "12"])
    assert (args.event_id, args.magnitude) == ("ies2026rudf", "")


def test_parse_manual_dry_run():
    args = scalert_event.parse_args(["--dry-run", "ies2026rudf"])
    assert args.dry_run and args.event_id == "ies2026rudf"


def test_bad_arguments_exit_code():
    assert scalert_event.main(["a", "b"]) == scalert_event.EXIT_BAD_ARGS


def test_sends_when_rules_say_so(run):
    assert len(run()) == 1


def test_every_recalculation_is_sent(run, make_assessment):
    assert len(run(assessment=make_assessment(Audience.ALL, 3.2))) == 1
    assert len(run(assessment=make_assessment(Audience.ALL, 3.2))) == 1
    assert len(run(assessment=make_assessment(Audience.STAFF, 2.9))) == 1


def test_nobody_sends_nothing(run, make_assessment, channels):
    assert run(assessment=make_assessment(None)) == []
    assert channels["sms"] == []


def test_sms_goes_to_the_same_audience(run, make_assessment, channels, settings):
    staff = make_assessment(Audience.STAFF, 2.9)
    run(assessment=staff)
    assert channels["sms"] == [staff]
    assert channels["sms_kwargs"][0]["recipients_file"] == settings.sms_recipients_file


def test_sms_is_sent_when_mail_fails(run, monkeypatch, channels):
    def broken_mail(*args, **kwargs):
        raise OSError("smtp down")

    monkeypatch.setattr(scalert_event, "send_event_mail", broken_mail)
    with pytest.raises(RuntimeError, match="MAIL"):
        run()
    assert len(channels["sms"]) == 1


def test_sms_can_be_turned_off(run, settings, channels):
    run(settings=replace(settings, send_sms=False))
    assert len(channels["mail"]) == 1 and channels["sms"] == []


def test_event_for_everyone_is_added_to_api(run, channels):
    run()
    assert channels["api"] == [{
        "seiscomp_oid": "ies1",
        "origin_time": "2026-09-08 04:52:15",
        "latitude": 41.607,
        "longitude": 43.5676,
        "depth": 15.3,
        "magnitudes": {"ML": 4.23},
        "location_ge": "საქართველო. ქალაქი გორი:5კმ.",
        "location_en": "Georgia. Gori (city).",
        "is_automatic": True,
    }]


def test_api_payload_is_rounded(run, channels):
    event = replace(
        EVENT, latitude=41.845951080322266, longitude=43.55186462402344,
        depth=10.123456, magnitudes={"ML": 1.943421827293825, "Mwp": 3.1},
    )
    run(event=event)
    payload = channels["api"][0]
    assert (payload["latitude"], payload["longitude"], payload["depth"]) == (41.84595, 43.55186, 10.123)
    assert payload["magnitudes"] == {"ML": 1.943}


def test_event_without_site_magnitude_is_not_added_to_api(run, channels):
    run(event=replace(EVENT, magnitudes={"Mwp": 3.1}))
    assert channels["api"] == []


def test_staff_only_event_is_added_to_api_too(run, make_assessment, channels):
    staff = make_assessment(Audience.STAFF, 2.9)
    assert staff.publish_iliauni is False
    run(assessment=staff)
    assert len(channels["api"]) == 1


def test_event_nobody_is_notified_about_is_not_added_to_api(run, make_assessment, channels):
    run(assessment=make_assessment(None))
    assert channels["api"] == []


def test_api_can_be_turned_off(run, settings, channels):
    run(settings=replace(settings, send_eq2api=False))
    assert channels["api"] == []


def test_api_failure_does_not_stop_mail_and_sms(run, monkeypatch, channels):
    class BrokenEventApiClient:
        def __init__(self, settings):
            pass

        def add_event(self, payload):
            raise EventApiError("api down")

    monkeypatch.setattr(scalert_event, "EventApiClient", BrokenEventApiClient)
    with pytest.raises(RuntimeError, match="API"):
        run()
    assert len(channels["mail"]) == 1 and len(channels["sms"]) == 1


def test_not_existing_event_is_skipped(run):
    assert run(event=replace(EVENT, event_type="not existing")) == []


def test_event_without_magnitude_is_skipped(run):
    assert run(event=replace(EVENT, magnitudes={})) == []


def test_main_logs_failure_and_returns_error(monkeypatch, settings):
    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(scalert_event, "load_event", boom)
    assert scalert_event.main(["msg", "1", "ies1", "5"]) == scalert_event.EXIT_FAILED
    log = settings.log_file.read_text(encoding="utf-8")
    assert "RECEIVED event_id=ies1 flag=new" in log
    assert "FAILED event_id=ies1" in log
    assert "db down" in log
    assert "Traceback" in log


def test_done_line_summarises_every_channel(run, caplog):
    caplog.set_level(logging.INFO)
    run()
    done = [r for r in caplog.records if r.getMessage().startswith("DONE")]
    assert len(done) == 1 and done[0].levelno == logging.INFO
    assert done[0].getMessage().startswith("DONE event_id=ies1 mail=sent sms=sent api=sent dry_run=False duration=")


def test_api_error_is_one_line_and_main_adds_no_second_traceback(monkeypatch, settings, make_assessment, channels):
    class BrokenEventApiClient:
        def __init__(self, settings):
            pass

        def add_event(self, payload):
            raise EventApiError("POST /api/seismic_events/ failed with HTTP 403: no permission", 403)

    monkeypatch.setattr(scalert_event, "EventApiClient", BrokenEventApiClient)
    monkeypatch.setattr(scalert_event, "load_event", lambda *a, **k: EVENT)
    monkeypatch.setattr(scalert_event, "process_event", lambda *a, **k: make_assessment())
    assert scalert_event.main(["ies1"]) == scalert_event.EXIT_FAILED

    log = settings.log_file.read_text(encoding="utf-8")
    assert "ERROR API FAILED event_id=ies1: POST /api/seismic_events/ failed with HTTP 403: no permission" in log
    assert "ERROR DONE event_id=ies1 mail=sent sms=sent api=failed" in log
    assert "Traceback" not in log
    assert "ERROR FAILED event_id=ies1" not in log


def test_unexpected_channel_error_keeps_its_traceback(run, monkeypatch, caplog):
    def broken_mail(*args, **kwargs):
        raise OSError("smtp down")

    monkeypatch.setattr(scalert_event, "send_event_mail", broken_mail)
    with pytest.raises(scalert_event.ChannelsFailed):
        run()
    failure = next(r for r in caplog.records if r.getMessage().startswith("MAIL FAILED"))
    assert failure.getMessage() == "MAIL FAILED event_id=ies1: unexpected error"
    assert failure.exc_info[1].args == ("smtp down",)


def test_event_not_in_database_is_one_line_without_traceback(monkeypatch, settings):
    def not_found(*args, **kwargs):
        raise EventNotReady("event ies1 not found")

    monkeypatch.setattr(scalert_event, "load_event", not_found)
    assert scalert_event.main(["ies1"]) == scalert_event.EXIT_FAILED
    log = settings.log_file.read_text(encoding="utf-8")
    assert "FAILED event_id=ies1: event ies1 not found" in log
    assert "Traceback" not in log

