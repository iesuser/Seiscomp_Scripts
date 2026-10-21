#!/home/sysop/Clone/Seiscomp_Scripts/scalert_event/venv/bin/python
# -*- coding: utf-8 -*-
"""Client for the seismic events API of the iesdata site.

`EventApiClient.add_event(event)` makes the site match `event`;
`publish_event(event_id)` / `unpublish_event(event_id)` then show it on, or
remove it from, WordPress.

`add_event` works in these steps:

    1. the event is validated; nothing is sent if it is invalid (ValueError);
    2. the site is searched for an event with the same `seiscomp_oid`;
    3. new event:      POST the event, then POST each magnitude. If a magnitude
                       fails, the new event is deleted again, so the site never
                       shows an event without magnitudes ("all or nothing");
    4. existing event: PUT the event fields, then PUT (known type) or POST (new
                       type) each magnitude. Magnitudes already on the site but
                       not in `event` are kept. Every magnitude is tried, and
                       the failed ones are reported together at the end.

An event is a dict with these keys (only the first four are required):

    seiscomp_oid   str, max 100   SeisComP event publicID, e.g. "ies2026ufhk"
    origin_time    str            UTC, ISO format "YYYY-MM-DD HH:MM:SS"
    latitude       float          -90 ... 90
    longitude      float          -180 ... 180
    magnitudes     dict           at least one, {site code: value}, e.g. {"ML": 3.4}
    depth          float          km
    location_ge    str, max 500
    location_en    str, max 500
    is_automatic   bool
    iesdata_id     str, max 100
    area           str, max 20

Endpoints used (all with the X-API-Key header):

    GET    /api/seismic_events/seiscomp_oid={oid}        lookup by seiscomp_oid (exact match)
    POST   /api/seismic_events/                          create an event
    PUT    /api/seismic_events/event_id={id}             update an event
    DELETE /api/seismic_events/event_id={id}             rollback of a failed create
    POST   /api/seismic_events/{id}/magnitudes           add a magnitude
    PUT    /api/seismic_events/magnitudes/{magnitude_id} change a magnitude's value
    POST   /api/publish_events/publish/{id}              publish (or update) on WordPress
    POST   /api/publish_events/unpublish/{id}            remove from WordPress

The full API description is served at /swagger.json.

Settings come from `.env` (see `config.EventApiSettings`): Send_eq2api_API_URL,
Send_eq2api_API_KEY (needs can_event_edit), SeisComp_Publisher_API_KEY (needs
can_event_publish) and, only for a self-signed server certificate, Send_eq2api_API_CA.

Manual, read-only lookup of an event on the site:
    ./send_eq2api/send_eq2api.py ies2026ufhk
"""

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import EventApiSettings, load_settings  # noqa: E402

# Magnitude codes the site knows (its `magnitudes` table). An unknown code
# would fail on the site, so it is rejected before anything is sent.
SITE_MAGNITUDE_CODES = frozenset({"ML", "MB", "MS", "MD", "MW", "K", "MPV", "MLH", "MC", "MLV", "M"})

REQUIRED_FIELDS = ("seiscomp_oid", "origin_time", "latitude", "longitude")
# Text fields and their maximum length on the site.
TEXT_FIELDS = {
    "seiscomp_oid": 100,
    "iesdata_id": 100,
    "area": 20,
    "location_ge": 500,
    "location_en": 500,
}
# Any other key (e.g. a typo) is rejected instead of being silently ignored by the site.
ALLOWED_FIELDS = frozenset({*REQUIRED_FIELDS, *TEXT_FIELDS, "depth", "magnitudes", "is_automatic"})

# Shown before the API's own message for these statuses.
HTTP_ERRORS = {
    401: "API key არასწორია",
    403: "სერვისს არ აქვს საჭირო უფლება",
}
# The API's 404 message for a missing event, as opposed to an unknown route.
EVENT_NOT_FOUND = "Seismic event not found"


class EventApiError(RuntimeError):
    """The API could not be reached or answered with an error."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status  # HTTP status; None for network errors


def validate_event(event: dict) -> None:
    """Raise ValueError if `event` does not match the format in the module docstring."""
    if not isinstance(event, dict):
        raise ValueError("Event must be a dict.")

    unknown = event.keys() - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"Unknown event key(s): {', '.join(sorted(unknown))}")

    for key in REQUIRED_FIELDS:
        if event.get(key) is None or event.get(key) == "":
            raise ValueError(f"{key} is required.")

    for key, max_len in TEXT_FIELDS.items():
        value = event.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > max_len):
            raise ValueError(f"{key} must be a string of at most {max_len} characters.")

    magnitudes = event.get("magnitudes")
    if not isinstance(magnitudes, dict) or not magnitudes:
        raise ValueError("Event must have at least one magnitude.")
    for code, value in magnitudes.items():
        if code not in SITE_MAGNITUDE_CODES:
            raise ValueError(f"Unknown magnitude code {code!r}; the site knows {', '.join(sorted(SITE_MAGNITUDE_CODES))}.")
        _to_float(value, f"magnitude {code}")

    try:
        datetime.fromisoformat(event["origin_time"])
    except (TypeError, ValueError):
        raise ValueError(f"Invalid origin_time: {event['origin_time']!r}") from None

    for key, limit in (("latitude", 90), ("longitude", 180)):
        if abs(_to_float(event[key], key)) > limit:
            raise ValueError(f"{key} must be between {-limit} and {limit}.")

    if event.get("depth") is not None:
        _to_float(event["depth"], "depth")

    if not isinstance(event.get("is_automatic", False), bool):
        raise ValueError("is_automatic must be a bool.")


def _to_float(value, name: str) -> float:
    """`value` as a finite float; bool, nan and inf are rejected."""
    # float(True), float("nan") and float("inf") all succeed, but none is a valid measurement.
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}: {value!r}") from None
    if isinstance(value, bool) or not math.isfinite(result):
        raise ValueError(f"Invalid {name}: {value!r}")
    return result


class EventApiClient:
    """Adds and updates events on the site. One instance can serve many events."""

    def __init__(self, settings: EventApiSettings, session: requests.Session | None = None):
        self.settings = settings
        self._base_url = settings.base_url.rstrip("/")
        self._session = session or requests.Session()

    def add_event(self, event: dict) -> dict:
        """Create `event` on the site, or update it if its seiscomp_oid is already there.

        Returns {"id": site event id, "created": True if it was new,
                 "is_published": whether it is on WordPress (always False for a new event)}.

        Raises:
            ValueError: `event` is invalid; nothing was sent.
            EventApiError: the API failed; see the module docstring for what is left behind.
        """
        validate_event(event)
        fields = {key: value for key, value in event.items() if key != "magnitudes" and value is not None}
        magnitudes = {code: _to_float(value, code) for code, value in event["magnitudes"].items()}

        existing = self.find_event(event["seiscomp_oid"])
        if existing is None:
            return {"id": self._create(fields, magnitudes), "created": True, "is_published": False}
        self._update(existing, fields, magnitudes)
        return {"id": existing["id"], "created": False, "is_published": bool(existing.get("is_published"))}

    def publish_event(self, event_id: int) -> dict:
        """Publish the site event `event_id` on WordPress, or update it there if already published.

        Returns the API response ({"message", "event_id", "published", "wp_response", "event"}).

        Raises:
            EventApiError: the API failed, or answered that the event was not published.
        """
        data = self._request("POST", f"/api/publish_events/publish/{event_id}", publisher=True)
        if not data.get("published"):
            raise EventApiError(f"Event #{event_id} was not published: {data.get('message') or 'no reason given'}")
        return data

    def unpublish_event(self, event_id: int) -> dict:
        """Remove the site event `event_id` from WordPress; it stays on the site itself.

        Returns the API response ({"message", "event_id", "published", "wp_response", "event"}).

        Raises:
            EventApiError: the API failed.
        """
        return self._request("POST", f"/api/publish_events/unpublish/{event_id}", publisher=True)

    def find_event(self, seiscomp_oid: str) -> dict | None:
        """The site's event with exactly this seiscomp_oid, or None."""
        path = f"/api/seismic_events/seiscomp_oid={quote(seiscomp_oid, safe='/')}"
        try:
            data = self._request("GET", path)
        except EventApiError as exc:
            # A wrong route is also a 404 ("The requested API URL was not found."); treating it as
            # "not on the site" would create a duplicate event on every recalculation.
            if exc.status == 404 and EVENT_NOT_FOUND in str(exc):
                return None
            raise
        event = data.get("event") if isinstance(data.get("event"), dict) else data
        return event if event.get("id") is not None else None

    def _create(self, fields: dict, magnitudes: dict[str, float]) -> int:
        event_id = self._request("POST", "/api/seismic_events/", fields)["event"]["id"]
        for code, value in magnitudes.items():
            try:
                self._add_magnitude(event_id, code, value)
            except EventApiError as exc:
                self._rollback(event_id, f"magnitude {code} failed: {exc}")
        return event_id

    def _rollback(self, event_id: int, reason: str) -> None:
        """Delete a half-created event, then raise EventApiError explaining why."""
        try:
            self._request("DELETE", f"/api/seismic_events/event_id={event_id}")
        except EventApiError as delete_exc:
            raise EventApiError(
                f"Event was not added: {reason}; rollback failed: {delete_exc}. "
                f"Event #{event_id} was left without magnitudes and must be deleted manually."
            ) from delete_exc
        raise EventApiError(f"Event was not added: {reason}")

    def _update(self, existing: dict, fields: dict, magnitudes: dict[str, float]) -> None:
        event_id = existing["id"]
        self._request("PUT", f"/api/seismic_events/event_id={event_id}", fields)

        # Site magnitude records by code; the record id is needed to change a value.
        on_site = {item["magnitude"]["code"].upper(): item for item in existing.get("magnitudes", [])}
        failed = []
        for code, value in magnitudes.items():
            try:
                if code.upper() in on_site:
                    self._request(
                        "PUT", f"/api/seismic_events/magnitudes/{on_site[code.upper()]['id']}", {"value": value},
                    )
                else:
                    self._add_magnitude(event_id, code, value)
            except EventApiError as exc:
                failed.append(f"{code}: {exc}")
        # The event existed before, so there is nothing to roll back; report what failed.
        if failed:
            raise EventApiError(f"Event #{event_id} magnitude update failed: {'; '.join(failed)}")

    def _add_magnitude(self, event_id: int, code: str, value: float) -> None:
        self._request(
            "POST", f"/api/seismic_events/{event_id}/magnitudes", {"magnitude_code": code, "value": value},
        )

    def _request(self, method: str, path: str, payload: dict | None = None, *, publisher: bool = False) -> dict:
        """Send one request and return the JSON response (an empty dict if it is not JSON).

        `publisher` selects the publishing key instead of the editing one.
        """
        if publisher:
            api_key, key_name = self.settings.publisher_api_key, "SeisComp_Publisher_API_KEY"
        else:
            api_key, key_name = self.settings.api_key, "Send_eq2api_API_KEY"
        if not api_key:
            raise EventApiError(f"{key_name} is not set")
        try:
            response = self._session.request(
                method,
                f"{self._base_url}{path}",
                json=payload,
                headers={"X-API-Key": api_key},
                timeout=self.settings.timeout_s,
                verify=str(self.settings.ca_file) if self.settings.ca_file else True,
            )
        except requests.RequestException as exc:
            raise EventApiError(f"Could not reach API: {exc}") from exc

        try:
            data = response.json()
        except ValueError:  # e.g. an HTML error page
            data = {}
        if not isinstance(data, dict):
            data = {}

        if not response.ok:
            message = " — ".join(
                text for text in (HTTP_ERRORS.get(response.status_code), data.get("message")) if text
            ) or "Unknown API error"
            raise EventApiError(
                f"{method} {path} failed with HTTP {response.status_code}: {message}", response.status_code,
            )
        return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show an event as stored on the iesdata site (read-only).")
    parser.add_argument("seiscomp_oid", help="SeisComP event publicID, e.g. ies2026ufhk")
    args = parser.parse_args(argv)

    client = EventApiClient(load_settings().event_api)
    try:
        event = client.find_event(args.seiscomp_oid)
    except EventApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if event is None:
        print(f"{args.seiscomp_oid} is not on the site.")
        return 1
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
