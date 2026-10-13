"""Entry point for processing an automatically detected earthquake.

`process_event` validates the event parameters, picks the preferred magnitude
and applies the notification rules. It only decides; delivery (email, SMS,
publishing) is the caller's job.
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from .borders_db import BordersRepository
from .location import LocationService
from .rules import Audience, decide

logger = logging.getLogger(__name__)

# Origin times are stored in UTC; notifications show Georgian local time (UTC+4, no DST).
GEORGIA_UTC_OFFSET = timedelta(hours=4)

# Magnitude types tried in this order. Any other type is used only when neither exists.
PREFERRED_MAGNITUDE_TYPES = ("ML", "M")

_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class EventAssessment:
    """Result of `process_event`.

    Attributes:
        audience: Who gets the notification: `Audience.ALL`, `Audience.STAFF`,
            or None when nobody is notified.
        publish: Whether the event may be published on the public website.
            Always False for staff-only events.
        location_ge: Georgian location text used in the notification, or None
            when nothing is sent.
        ev_mode: "Automatic" or "Manual", as shown in the notification text.
        magnitude_type: Type of the magnitude the decision was based on, e.g. "ML".
        magnitude: That magnitude's value, rounded to two decimals.
        local_time: Origin time converted to Georgian local time.
        reason: Georgian explanation of the outcome, including the numbers
            (distances, accelerations) it was based on.
    """

    audience: Audience | None
    publish: bool
    location_ge: str | None
    ev_mode: str
    magnitude_type: str
    magnitude: float
    local_time: datetime
    reason: str

    @property
    def send(self) -> bool:
        """True when at least one group of recipients should be notified."""
        return self.audience is not None

    def to_dict(self) -> dict:
        """JSON-friendly representation (enum as string, time as text)."""
        return {
            "send": self.send,
            "audience": self.audience.value if self.audience else None,
            "publish": self.publish,
            "location_ge": self.location_ge,
            "ev_mode": self.ev_mode,
            "magnitude_type": self.magnitude_type,
            "magnitude": self.magnitude,
            "local_time": self.local_time.strftime(_TIME_FORMAT),
            "reason": self.reason,
        }


def process_event(
    org_time: datetime | str,
    org_lat: float,
    org_lon: float,
    org_depth: float,
    org_ev_mode: str | bool,
    magnitudes: Mapping[str, float],
    *,
    locations: LocationService | None = None,
) -> EventAssessment:
    """Decide who should be notified about an earthquake and describe its location.

    Args:
        org_time: Origin time in UTC, as a datetime or "YYYY-MM-DD HH:MM:SS".
        org_lat, org_lon: Epicentre coordinates in degrees.
        org_depth: Hypocentre depth in km.
        org_ev_mode: "automatic"/"manual", or a bool meaning "is automatic".
        magnitudes: Magnitude values keyed by type, e.g. {"ML": 3.4}.
        locations: Spatial lookup to use. When omitted, a connection to the
            borders database is opened for the duration of the call. Tests pass
            a fake here so no database is needed.

    Raises:
        ValueError: a required parameter is missing or malformed, or there is
            no usable magnitude.
        BordersDbError: the borders database could not be reached or queried.
    """
    lat = _require_float(org_lat, "org_lat")
    lon = _require_float(org_lon, "org_lon")
    depth = _require_float(org_depth, "org_depth")
    local_time = _parse_utc(org_time) + GEORGIA_UTC_OFFSET
    ev_mode = _normalize_ev_mode(org_ev_mode)
    magnitude_type, magnitude = choose_preferred_magnitude(magnitudes)
    magnitude = round(magnitude, 2)

    logger.debug(
        "Rule inputs: lat=%s lon=%s depth=%s magnitude=%s%s (from %s)",
        lat, lon, depth, magnitude, magnitude_type, dict(magnitudes),
    )
    if locations is None:
        # The connection is closed as soon as the decision is made.
        with BordersRepository.connect() as repository:
            decision = decide(LocationService(repository), lat, lon, depth, magnitude)
    else:
        decision = decide(locations, lat, lon, depth, magnitude)

    return EventAssessment(
        audience=decision.audience,
        publish=decision.publish,
        location_ge=decision.location_ge,
        ev_mode=ev_mode,
        magnitude_type=magnitude_type,
        magnitude=magnitude,
        local_time=local_time,
        reason=decision.reason,
    )


def choose_preferred_magnitude(magnitudes: Mapping[str, float]) -> tuple[str, float]:
    """Return (type, value), preferring ML, then M, then the first available type.

    Entries whose value is None are ignored.

    Raises:
        ValueError: no magnitude has a value.
    """
    available = {
        str(mag_type): float(value)
        for mag_type, value in (magnitudes or {}).items()
        if value is not None
    }
    if not available:
        raise ValueError("magnitudes must contain at least one value")

    for preferred in PREFERRED_MAGNITUDE_TYPES:
        if preferred in available:
            return preferred, available[preferred]
    return next(iter(available.items()))


def _require_float(value, name: str) -> float:
    """Convert a required numeric parameter, naming it in the error message."""
    if value is None or value == "":
        raise ValueError(f"{name} is required")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}: {value!r}") from None


def _parse_utc(org_time: datetime | str) -> datetime:
    """Parse a naive UTC timestamp, dropping fractional seconds.

    Accepts a datetime, "YYYY-MM-DD HH:MM:SS" or the ISO form with a "T" separator.
    """
    if isinstance(org_time, datetime):
        return org_time.replace(tzinfo=None, microsecond=0)
    text = str(org_time).strip().replace("T", " ").split(".", 1)[0]
    try:
        return datetime.strptime(text, _TIME_FORMAT)
    except ValueError:
        raise ValueError(f"Invalid org_time: {org_time!r}") from None


def _normalize_ev_mode(org_ev_mode: str | bool) -> str:
    """Return the evaluation mode as shown in notifications ("Automatic" / "Manual")."""
    if isinstance(org_ev_mode, bool):
        return "Automatic" if org_ev_mode else "Manual"
    text = str(org_ev_mode or "").strip()
    if not text:
        raise ValueError("org_ev_mode is required")
    return text.capitalize()
