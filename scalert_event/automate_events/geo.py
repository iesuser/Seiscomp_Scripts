"""Pure geometry helpers. No database or I/O access.

All coordinates are decimal degrees, passed as (latitude, longitude).
"""

import math
from collections.abc import Sequence

# Mean Earth radius used by the haversine formula.
EARTH_RADIUS_KM = 6371.0

# Upper bounds (exclusive) of each compass sector, in degrees counter-clockwise
# from east. Anything at or above the last bound wraps back to east.
_COMPASS_SECTORS_GE = (
    (23.0, "აღმოსავლეთით"),  # east
    (68.0, "ჩრდილო-აღმოსავლეთით"),  # north-east
    (113.0, "ჩრდილოეთით"),  # north
    (158.0, "ჩრდილო-დასავლეთით"),  # north-west
    (203.0, "დასავლეთით"),  # west
    (248.0, "სამხრეთ-დასავლეთით"),  # south-west
    (293.0, "სამხრეთით"),  # south
    (338.0, "სამხრეთ-აღმოსავლეთით"),  # south-east
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def planar_bearing_degrees(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> float:
    """Angle of the vector from one point to another, in degrees [0, 360).

    Measured counter-clockwise from east on a flat lat/lon plane, which is
    accurate enough for the short regional distances used in alert texts.
    Identical points return 90 (north), matching the historic behaviour.
    """
    d_lat = to_lat - from_lat
    d_lon = to_lon - from_lon
    if d_lat == 0 and d_lon == 0:
        return 90.0
    return math.degrees(math.atan2(d_lat, d_lon)) % 360.0


def compass_direction_ge(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> str:
    """Georgian compass word describing where `to` lies relative to `from`.

    Example: a point north-east of a city gives "ჩრდილო-აღმოსავლეთით".
    """
    bearing = planar_bearing_degrees(from_lat, from_lon, to_lat, to_lon)
    for upper_bound, label in _COMPASS_SECTORS_GE:
        if bearing < upper_bound:
            return label
    return _COMPASS_SECTORS_GE[0][1]


def point_in_polygon(lat: float, lon: float, polygon: Sequence[tuple[float, float]]) -> bool:
    """Ray-casting test for a point against a polygon of (lat, lon) vertices.

    A ray is cast from the point towards increasing latitude; every polygon edge
    it crosses flips `inside`. An odd number of crossings means the point is
    inside. The polygon does not need to be explicitly closed.
    """
    if not polygon:
        raise ValueError("polygon must contain at least one vertex")

    inside = False
    vertex_count = len(polygon)
    p1_lat, p1_lon = polygon[0]
    # vertex_count + 1 steps so the last vertex is joined back to the first.
    for index in range(vertex_count + 1):
        p2_lat, p2_lon = polygon[index % vertex_count]
        # Does this edge span the point's longitude, with part of it north of the point?
        if min(p1_lon, p2_lon) < lon <= max(p1_lon, p2_lon) and lat <= max(p1_lat, p2_lat):
            if p1_lat == p2_lat:
                inside = not inside
            else:
                # Latitude where the edge crosses the point's longitude.
                lat_intersection = (lon - p1_lon) * (p2_lat - p1_lat) / (p2_lon - p1_lon) + p1_lat
                if lat <= lat_intersection:
                    inside = not inside
        p1_lat, p1_lon = p2_lat, p2_lon
    return inside


def min_distance_km(lat: float, lon: float, points: Sequence[tuple[float, float]]) -> float:
    """Shortest great-circle distance from a point to any of the given points."""
    if not points:
        raise ValueError("points must not be empty")
    return min(haversine_km(lat, lon, p_lat, p_lon) for p_lat, p_lon in points)
