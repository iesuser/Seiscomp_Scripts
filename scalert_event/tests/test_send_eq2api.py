from dataclasses import replace
from datetime import datetime

import pytest
import requests

from config import EventApiSettings
from seiscomp_db import EventData
from send_eq2api.event_sender import build_event_payload, send_event_api, site_magnitudes
from send_eq2api.send_eq2api import EventApiClient, EventApiError, validate_event

BASE = "https://iesdata.test:3030"
SETTINGS = EventApiSettings(
    base_url=BASE + "/", api_key="edit-key", publisher_api_key="publish-key", ca_file=None, timeout_s=5,
)

EVENT = {
    "seiscomp_oid": "ies1",
    "origin_time": "2026-10-12 09:35:14",
    "latitude": 41.84595,
    "longitude": 43.55186,
    "depth": 0.0,
    "magnitudes": {"ML": 1.943, "M": 2.759},
    "location_ge": "საქართველო.",
    "location_en": "Georgia.",
    "is_automatic": False,
}


class FakeResponse:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self.ok = status < 400
        self._data = data

    def json(self):
        if self._data is None:
            raise ValueError("not JSON")
        return self._data


class FakeSession:
    """Answers requests from `routes` {(method, path): FakeResponse}; unknown routes get {}."""

    def __init__(self, routes=None):
        self.routes = routes or {}
        self.calls = []
        self.keys = []

    def request(self, method, url, *, json, headers, timeout, verify):
        path = url.removeprefix(BASE)
        self.calls.append((method, path, json))
        self.keys.append(headers["X-API-Key"])
        answer = self.routes.get((method, path), FakeResponse(200, {}))
        if isinstance(answer, Exception):
            raise answer
        return answer


def client(routes=None):
    session = FakeSession(routes)
    return EventApiClient(SETTINGS, session=session), session


LOOKUP = "/api/seismic_events/seiscomp_oid/ies1"
NOT_FOUND = {("GET", LOOKUP): FakeResponse(404, {"error": "not_found", "message": "Not found"})}
CREATED = {("POST", "/api/seismic_events/"): FakeResponse(201, {"event": {"id": 7}})}


def test_new_event_is_created_with_its_magnitudes():
    api, session = client({**NOT_FOUND, **CREATED})
    assert api.add_event(EVENT) == {"id": 7, "created": True, "is_published": False}
    assert [(m, p) for m, p, _ in session.calls] == [
        ("GET", LOOKUP),
        ("POST", "/api/seismic_events/"),
        ("POST", "/api/seismic_events/7/magnitudes"),
        ("POST", "/api/seismic_events/7/magnitudes"),
    ]
    assert "magnitudes" not in session.calls[1][2]
    assert session.calls[2][2] == {"magnitude_code": "ML", "value": 1.943}


def test_failed_magnitude_rolls_back_the_new_event():
    api, session = client({
        **NOT_FOUND, **CREATED,
        ("POST", "/api/seismic_events/7/magnitudes"): FakeResponse(400, {"message": "bad magnitude"}),
    })
    with pytest.raises(EventApiError, match="Event was not added: magnitude ML failed.*bad magnitude"):
        api.add_event(EVENT)
    assert session.calls[-1][:2] == ("DELETE", "/api/seismic_events/7")


def test_failed_rollback_says_the_event_must_be_deleted_manually():
    api, _ = client({
        **NOT_FOUND, **CREATED,
        ("POST", "/api/seismic_events/7/magnitudes"): FakeResponse(500),
        ("DELETE", "/api/seismic_events/7"): FakeResponse(500),
    })
    with pytest.raises(EventApiError, match="#7 was left without magnitudes"):
        api.add_event(EVENT)


def test_existing_event_is_updated_and_new_magnitude_added():
    existing = {"seiscomp_oid": "ies1", "id": 3, "magnitudes": [{"id": 30, "magnitude": {"code": "ml"}}]}
    api, session = client({("GET", LOOKUP): FakeResponse(200, existing)})
    assert api.add_event(EVENT) == {"id": 3, "created": False, "is_published": False}
    assert [(m, p, j) for m, p, j in session.calls[1:] if p != "/api/seismic_events/3"] == [
        ("PUT", "/api/seismic_events/magnitudes/30", {"value": 1.943}),
        ("POST", "/api/seismic_events/3/magnitudes", {"magnitude_code": "M", "value": 2.759}),
    ]


def test_update_tries_every_magnitude_and_reports_the_failed_ones():
    existing = {"seiscomp_oid": "ies1", "id": 3, "magnitudes": []}
    api, session = client({
        ("GET", LOOKUP): FakeResponse(200, existing),
        ("POST", "/api/seismic_events/3/magnitudes"): FakeResponse(400, {"message": "nope"}),
    })
    with pytest.raises(EventApiError, match="#3 magnitude update failed: ML: .*; M: "):
        api.add_event(EVENT)
    assert not any(method == "DELETE" for method, _, _ in session.calls)


def test_http_errors_use_our_text_for_401():
    api, _ = client({("GET", LOOKUP): FakeResponse(401, {"message": "Unauthorized"})})
    with pytest.raises(EventApiError, match="API key არასწორია") as exc:
        api.find_event("ies1")
    assert exc.value.status == 401


def test_network_error_becomes_event_api_error():
    api, _ = client({("GET", LOOKUP): requests.ConnectionError("refused")})
    with pytest.raises(EventApiError, match="Could not reach API") as exc:
        api.find_event("ies1")
    assert exc.value.status is None


def test_missing_api_key_sends_nothing():
    session = FakeSession()
    api = EventApiClient(replace(SETTINGS, api_key=""), session=session)
    with pytest.raises(EventApiError, match="Send_eq2api_API_KEY"):
        api.add_event(EVENT)
    assert session.calls == []


@pytest.mark.parametrize("change, message", [
    ({"magnitudes": {}}, "at least one magnitude"),
    ({"magnitudes": {"MLv": 2.2}}, "Unknown magnitude code 'MLv'"),
    ({"magnitudes": {"ML": float("nan")}}, "Invalid magnitude ML"),
    ({"latitude": 91}, "latitude must be between"),
    ({"origin_time": "12.10.2026"}, "Invalid origin_time"),
    ({"is_automatic": "True"}, "is_automatic must be a bool"),
    ({"location_en": "x" * 501}, "location_en must be a string of at most 500"),
    ({"locaton_en": "typo"}, "Unknown event key"),
    ({"seiscomp_oid": ""}, "seiscomp_oid is required"),
])
def test_invalid_event_is_rejected_before_sending(change, message):
    with pytest.raises(ValueError, match=message):
        validate_event({**EVENT, **change})


def test_site_magnitudes_map_seiscomp_types():
    magnitudes, skipped = site_magnitudes({
        "ML": 1.943421827, "MLv": 2.2257414, "mb": 4.6399244, "mB": 4.7,
        "Mw": 3.01, "Ms_20": 3.5, "Mwp": 3.1, "M": 2.758707,
    })
    assert magnitudes == {"ML": 1.943, "MLV": 2.226, "MB": 4.64, "MW": 3.01, "MS": 3.5, "M": 2.759}
    assert skipped == ["mB", "Mwp"]


def test_payload_built_from_seiscomp_is_valid(make_assessment):
    event = EventData(
        event_id="ies2026ufhk", origin_id="Origin/1", origin_time=datetime(2026, 10, 12, 9, 35, 14, 500000),
        latitude=41.845951080322266, longitude=43.55186462402344, depth=10.123456,
        evaluation_mode="manual", event_type="earthquake", magnitudes={"ML": 1.94342},
    )
    magnitudes, _ = site_magnitudes(event.magnitudes)
    payload = build_event_payload(event, make_assessment(), magnitudes)
    validate_event(payload)
    assert payload["origin_time"] == "2026-10-12 09:35:14"
    assert (payload["latitude"], payload["longitude"], payload["depth"]) == (41.84595, 43.55186, 10.123)
    assert payload["is_automatic"] is False


SEISCOMP_EVENT = EventData(
    "ies1", "Origin/1", datetime(2026, 10, 12), 41.8, 43.5, 10, "automatic", "earthquake", {"ML": 3.4},
)
PUBLISHED = {
    ("POST", "/api/publish_events/publish/7"): FakeResponse(200, {"published": True, "message": "Publish request completed.", "wp_response": "1"}),
}


def test_only_send_api_decides_whether_the_site_gets_the_event(make_assessment):
    api, session = client({**NOT_FOUND, **CREATED, **PUBLISHED})
    assert send_event_api(SEISCOMP_EVENT, replace(make_assessment(), send_api=False), client=api) is False
    assert session.calls == []
    assert send_event_api(SEISCOMP_EVENT, make_assessment(), client=api) is True


def test_publish_iliauni_publishes_with_the_publisher_key(make_assessment):
    api, session = client({**NOT_FOUND, **CREATED, **PUBLISHED})
    send_event_api(SEISCOMP_EVENT, make_assessment(), client=api)
    assert session.calls[-1][:2] == ("POST", "/api/publish_events/publish/7")
    assert session.keys[-1] == "publish-key"
    assert set(session.keys[:-1]) == {"edit-key"}


def test_staff_only_event_is_added_but_not_published(make_assessment):
    from automate_events import Audience

    api, session = client({**NOT_FOUND, **CREATED})
    assert send_event_api(SEISCOMP_EVENT, make_assessment(Audience.STAFF, 2.9), client=api) is True
    assert ("POST", "/api/seismic_events/") in [(m, p) for m, p, _ in session.calls]
    assert not any("publish_events" in p for _, p, _ in session.calls)


def found(is_published):
    item = {"seiscomp_oid": "ies1", "id": 3, "magnitudes": [], "is_published": is_published}
    return {("GET", LOOKUP): FakeResponse(200, item)}


def wordpress_calls(session):
    return [path for _, path, _ in session.calls if "publish_events" in path]


def test_event_downgraded_to_staff_is_unpublished(make_assessment):
    from automate_events import Audience

    api, session = client(found(is_published=True))
    send_event_api(SEISCOMP_EVENT, make_assessment(Audience.STAFF, 2.9), client=api)
    assert wordpress_calls(session) == ["/api/publish_events/unpublish/3"]
    assert session.keys[-1] == "publish-key"


def test_staff_event_never_published_is_not_unpublished(make_assessment):
    from automate_events import Audience

    api, session = client(found(is_published=False))
    send_event_api(SEISCOMP_EVENT, make_assessment(Audience.STAFF, 2.9), client=api)
    assert wordpress_calls(session) == []


def test_published_event_for_everyone_is_published_again_not_unpublished(make_assessment):
    api, session = client({
        **found(is_published=True),
        ("POST", "/api/publish_events/publish/3"): FakeResponse(200, {"published": True}),
    })
    send_event_api(SEISCOMP_EVENT, make_assessment(), client=api)
    assert wordpress_calls(session) == ["/api/publish_events/publish/3"]


def test_publish_answered_not_published_is_an_error():
    api, _ = client({("POST", "/api/publish_events/publish/7"): FakeResponse(200, {"published": False, "message": "WP down"})})
    with pytest.raises(EventApiError, match="#7 was not published: WP down"):
        api.publish_event(7)


def test_missing_publisher_key_is_reported_by_name():
    api, session = client()
    api = EventApiClient(replace(SETTINGS, publisher_api_key=""), session=session)
    with pytest.raises(EventApiError, match="SeisComp_Publisher_API_KEY is not set"):
        api.publish_event(7)
    assert session.calls == []


def test_403_shows_our_text_and_the_api_reason():
    api, _ = client({("POST", "/api/publish_events/publish/7"): FakeResponse(
        403, {"error": "forbidden", "message": "Missing required permission: can_event_publish"},
    )})
    with pytest.raises(EventApiError, match="საჭირო უფლება — Missing required permission: can_event_publish"):
        api.publish_event(7)


def test_dry_run_sends_nothing(make_assessment):
    api, session = client()
    assert send_event_api(SEISCOMP_EVENT, make_assessment(), client=api, dry_run=True) is False
    assert session.calls == []
