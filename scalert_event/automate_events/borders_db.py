"""Read-only access to the `ies_borders` MySQL database.

The database holds border polygons (one table per region, one row per vertex),
Caucasus cities and Georgian settlements. It is a separate database from the
SeisComP one.

Connection settings come from environment variables (see `.env.example`):
BORDERS_DB_HOST, BORDERS_DB_USER, BORDERS_DB_PASSWORD (required), BORDERS_DB_NAME.
"""

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import pymysql

logger = logging.getLogger(__name__)

# Polygon vertices as (latitude, longitude) pairs, in the order stored in the table.
Polygon = tuple[tuple[float, float], ...]

# Table names cannot be bound as SQL parameters, so only these are accepted.
POLYGON_TABLES = frozenset(
    {
        "border_georgia",
        "border_turkey",
        "border_arminia",
        "border_azerbaijan",
        "border_russia",
        "border_black_sea",
        "subborder_turkey_taoklarjeti",
        "subborder_russia_adigea",
        "subborder_russia_chechnia",
        "subborder_russia_dagestan",
        "subborder_russia_ingusheti",
        "subborder_russia_kabardino_balkaria",
        "subborder_russia_karachai",
        "subborder_russia_krasnodar",
        "subborder_russia_north_oseti",
        "subborder_tbilisi",
        "subborder_tbilisi_didgori",
        "subborder_tbilisi_didube_chughureti",
        "subborder_tbilisi_gldani_nadzaladevi",
        "subborder_tbilisi_isani_samgori",
        "subborder_tbilisi_old_tbilisi",
        "subborder_tbilisi_vake_saburtalo",
    }
)


class BordersDbError(RuntimeError):
    """The borders database is unreachable or returned unusable data."""


@dataclass(frozen=True)
class BordersDbSettings:
    """Connection parameters for the borders database."""

    host: str
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "BordersDbSettings":
        """Read settings from the environment; only the password has no default."""
        password = os.getenv("BORDERS_DB_PASSWORD")
        if not password:
            raise BordersDbError("BORDERS_DB_PASSWORD is not set")
        return cls(
            host=os.getenv("BORDERS_DB_HOST", "127.0.0.1"),
            user=os.getenv("BORDERS_DB_USER", "ies_borders"),
            password=password,
            database=os.getenv("BORDERS_DB_NAME", "ies_borders"),
        )


@dataclass(frozen=True)
class City:
    """A row of `cities_caucasus`.

    `status_ge` is the settlement type shown before the name (e.g. "ქალაქი").
    `radius_km` approximates the city's size; distances are measured from its edge.
    """

    latitude: float
    longitude: float
    name_ge: str
    status_ge: str
    radius_km: int


@dataclass(frozen=True)
class Settlement:
    """A row of `settlements_georgia` (villages, small towns)."""

    latitude: float
    longitude: float
    name_ge: str
    status_ge: str


class BordersRepository:
    """Queries a single open connection.

    Each table is read at most once per instance and cached, because the rules
    ask about the same polygons several times while deciding one event.
    Create one instance per event (via `connect`) so data is never stale.
    """

    def __init__(self, connection):
        self._connection = connection
        self._polygons: dict[str, Polygon] = {}
        self._cities: tuple[City, ...] | None = None
        self._settlements: tuple[Settlement, ...] | None = None

    @classmethod
    @contextmanager
    def connect(cls, settings: BordersDbSettings | None = None) -> Iterator["BordersRepository"]:
        """Open a connection for the duration of the `with` block, then close it.

        Raises:
            BordersDbError: settings are incomplete or the connection failed.
        """
        settings = settings or BordersDbSettings.from_env()
        try:
            connection = pymysql.connect(
                host=settings.host,
                user=settings.user,
                password=settings.password,
                database=settings.database,
                charset="utf8",
            )
        except pymysql.Error as exc:
            logger.error("Could not connect to borders database: %s", exc)
            raise BordersDbError("Could not connect to borders database") from exc

        try:
            yield cls(connection)
        finally:
            connection.close()

    def polygon(self, table: str) -> Polygon:
        """Vertices of the polygon stored in `table`.

        Raises:
            ValueError: `table` is not in `POLYGON_TABLES`.
            BordersDbError: the table is empty or the query failed.
        """
        if table not in POLYGON_TABLES:
            raise ValueError(f"Unknown border table: {table}")
        if table not in self._polygons:
            rows = self._fetch(f"SELECT latitude, longitude FROM `{table}`")
            if not rows:
                raise BordersDbError(f"Border table is empty: {table}")
            self._polygons[table] = tuple((float(lat), float(lon)) for lat, lon in rows)
        return self._polygons[table]

    def cities(self) -> tuple[City, ...]:
        """Caucasus cities, excluding Tbilisi (it is described by district instead)."""
        if self._cities is None:
            rows = self._fetch(
                "SELECT latitude, longitude, name_ge, status_ge, radius "
                "FROM cities_caucasus WHERE status_en != 'tbilisi'"
            )
            self._cities = tuple(
                City(float(lat), float(lon), name, status, int(radius))
                for lat, lon, name, status, radius in rows
            )
        return self._cities

    def settlements(self) -> tuple[Settlement, ...]:
        """All Georgian settlements."""
        if self._settlements is None:
            rows = self._fetch(
                "SELECT latitude, longitude, name_ge, status_ge FROM settlements_georgia"
            )
            self._settlements = tuple(
                Settlement(float(lat), float(lon), name, status)
                for lat, lon, name, status in rows
            )
        return self._settlements

    def _fetch(self, sql: str) -> tuple:
        """Run a read-only query and return all rows, wrapping driver errors."""
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchall()
        except pymysql.Error as exc:
            logger.error("Borders database query failed: %s", exc)
            raise BordersDbError("Borders database query failed") from exc
