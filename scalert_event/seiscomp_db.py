"""Read-only access to the SeisComP MySQL database.

`load_event(event_id)` returns the event's preferred origin and all magnitudes
computed for that origin.

scalert receives events from the messaging system while `scdb` writes them to
the database asynchronously, so right after a new event the row (or its new
preferred origin) may not exist yet. `load_event` therefore retries for a while
before giving up.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pymysql

from config import SeiscompDbSettings

logger = logging.getLogger(__name__)

# Event.type values that mean "this is not a real event"; such events are never sent.
NOT_REAL_EVENT_TYPES = frozenset({"not existing", "not locatable", "outside of network interest"})

_EVENT_SQL = """
    SELECT E.preferredOriginID, E.preferredMagnitudeID, E.type
    FROM PublicObject AS PE
    JOIN Event AS E ON E._oid = PE._oid
    WHERE PE.publicID = %s
"""

_ORIGIN_SQL = """
    SELECT O._oid, O.time_value, O.time_value_ms, O.latitude_value, O.longitude_value,
           O.depth_value, O.evaluationMode
    FROM PublicObject AS PO
    JOIN Origin AS O ON O._oid = PO._oid
    WHERE PO.publicID = %s
"""

_MAGNITUDES_SQL = """
    SELECT PM.publicID, M.type, M.magnitude_value
    FROM Magnitude AS M
    JOIN PublicObject AS PM ON PM._oid = M._oid
    WHERE M._parent_oid = %s
"""


class EventNotReady(LookupError):
    """The event or its preferred origin is not (yet) in the database."""


@dataclass(frozen=True)
class EventData:
    """Everything the decision needs, as stored in SeisComP.

    Attributes:
        event_id: Event publicID, e.g. "ies2026rudf".
        origin_id: publicID of the preferred origin.
        origin_time: Origin time in UTC (naive datetime).
        latitude, longitude: Epicentre in degrees.
        depth: Depth in km.
        evaluation_mode: "automatic" or "manual".
        event_type: Event.type, e.g. "earthquake", or None when not set.
        magnitudes: All magnitudes of the preferred origin, e.g. {"ML": 3.4, "M": 3.4}.
        preferred_magnitude_type: Type of Event.preferredMagnitudeID, if it is
            one of `magnitudes`.
    """

    event_id: str
    origin_id: str
    origin_time: datetime
    latitude: float
    longitude: float
    depth: float
    evaluation_mode: str
    event_type: str | None
    magnitudes: dict[str, float] = field(default_factory=dict)
    preferred_magnitude_type: str | None = None

    @property
    def is_real_event(self) -> bool:
        return self.event_type not in NOT_REAL_EVENT_TYPES


def connect(settings: SeiscompDbSettings):
    """Open a connection to the SeisComP database."""
    return pymysql.connect(
        host=settings.host,
        user=settings.user,
        password=settings.password,
        database=settings.database,
        charset="utf8",
    )


def load_event(
    event_id: str,
    settings: SeiscompDbSettings,
    *,
    retries: int = 5,
    retry_delay_s: float = 3.0,
) -> EventData:
    """Load `event_id`, retrying while it, its origin or its magnitudes are missing.

    Returns the data even if it still has no magnitudes after all retries; the
    caller decides what to do with such an event.

    Raises:
        EventNotReady: the event or its preferred origin was never found.
        pymysql.Error: the database could not be reached or queried.
    """
    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        connection = connect(settings)
        try:
            data = _read_event(connection, event_id)
        except EventNotReady as exc:
            if attempt == attempts:
                raise
            logger.info("WAITING event_id=%s attempt=%d/%d: %s", event_id, attempt, attempts, exc)
        else:
            if data.magnitudes or attempt == attempts:
                return data
            logger.info(
                "WAITING event_id=%s attempt=%d/%d: origin %s has no magnitudes yet",
                event_id, attempt, attempts, data.origin_id,
            )
        finally:
            connection.close()
        time.sleep(retry_delay_s)
    raise AssertionError("unreachable")


def _read_event(connection, event_id: str) -> EventData:
    with connection.cursor() as cursor:
        cursor.execute(_EVENT_SQL, (event_id,))
        event_row = cursor.fetchone()
        if event_row is None:
            raise EventNotReady(f"event {event_id} not found")
        origin_id, preferred_magnitude_id, event_type = event_row
        if not origin_id:
            raise EventNotReady(f"event {event_id} has no preferred origin")

        cursor.execute(_ORIGIN_SQL, (origin_id,))
        origin_row = cursor.fetchone()
        if origin_row is None:
            raise EventNotReady(f"preferred origin {origin_id} not found")
        origin_oid, time_value, time_ms, lat, lon, depth, mode = origin_row

        cursor.execute(_MAGNITUDES_SQL, (origin_oid,))
        magnitude_rows = cursor.fetchall()

    magnitudes = {}
    preferred_type = None
    for public_id, mag_type, value in magnitude_rows:
        if mag_type is None or value is None:
            continue
        magnitudes[mag_type] = float(value)
        if public_id == preferred_magnitude_id:
            preferred_type = mag_type

    return EventData(
        event_id=event_id,
        origin_id=origin_id,
        origin_time=time_value + timedelta(microseconds=time_ms or 0),
        latitude=float(lat),
        longitude=float(lon),
        depth=float(depth) if depth is not None else 0.0,
        evaluation_mode=mode or "automatic",
        event_type=event_type,
        magnitudes=magnitudes,
        preferred_magnitude_type=preferred_type,
    )
