from datetime import datetime

import pytest

import seiscomp_db
from config import SeiscompDbSettings
from seiscomp_db import EventNotReady, load_event

SETTINGS = SeiscompDbSettings("h", "u", "p", "d")
EVENT_ROW = ("Origin/1", "Origin/1/netMag/M", "earthquake")
ORIGIN_ROW = (77, datetime(2026, 9, 8, 4, 52, 15), 375168, 41.607, 43.5676, 15.3, "automatic")
MAGNITUDE_ROWS = (("Origin/1/netMag/ML", "ML", 4.23), ("Origin/1/netMag/M", "M", 4.2))


class FakeCursor:
    def __init__(self, results):
        self.results = results
        self.queries = []
        self._last = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params):
        self.queries.append(params)
        self._last = self.results.pop(0)

    def fetchone(self):
        return self._last

    def fetchall(self):
        return self._last


class FakeConnection:
    def __init__(self, results):
        self.cursor_obj = FakeCursor(results)
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def close(self):
        self.closed = True


def install(monkeypatch, *result_sets):
    """Each element of `result_sets` is the list of query results for one connection."""
    connections = [FakeConnection(list(results)) for results in result_sets]
    pending = list(connections)
    monkeypatch.setattr(seiscomp_db, "connect", lambda settings: pending.pop(0))
    monkeypatch.setattr(seiscomp_db.time, "sleep", lambda s: None)
    return connections


def test_loads_preferred_origin_and_magnitudes(monkeypatch):
    (conn,) = install(monkeypatch, [EVENT_ROW, ORIGIN_ROW, MAGNITUDE_ROWS])
    data = load_event("ies2026rudf", SETTINGS)
    assert data.origin_id == "Origin/1"
    assert data.origin_time == datetime(2026, 9, 8, 4, 52, 15, 375168)
    assert (data.latitude, data.longitude, data.depth) == (41.607, 43.5676, 15.3)
    assert data.magnitudes == {"ML": 4.23, "M": 4.2}
    assert data.preferred_magnitude_type == "M"
    assert data.is_real_event
    assert conn.cursor_obj.queries[0] == ("ies2026rudf",)
    assert conn.closed


def test_retries_until_event_appears(monkeypatch):
    install(monkeypatch, [None], [EVENT_ROW, ORIGIN_ROW, MAGNITUDE_ROWS])
    assert load_event("ies1", SETTINGS, retries=3).magnitudes


def test_gives_up_when_event_never_appears(monkeypatch):
    install(monkeypatch, [None], [None])
    with pytest.raises(EventNotReady):
        load_event("ies1", SETTINGS, retries=2)


def test_returns_without_magnitudes_after_retries(monkeypatch):
    install(monkeypatch, [EVENT_ROW, ORIGIN_ROW, ()], [EVENT_ROW, ORIGIN_ROW, ()])
    assert load_event("ies1", SETTINGS, retries=2).magnitudes == {}


def test_not_existing_event_is_not_real(monkeypatch):
    install(monkeypatch, [("Origin/1", None, "not existing"), ORIGIN_ROW, MAGNITUDE_ROWS])
    assert not load_event("ies1", SETTINGS).is_real_event
