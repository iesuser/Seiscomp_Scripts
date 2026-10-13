"""Decides who should be notified about an earthquake.

Georgia:
    mag >= 3.0                                  -> everyone
    Tbilisi, 2.8 <= mag < 3.0                   -> everyone
    Tbilisi, mag < 2.8                          -> nobody
    Outside Tbilisi, 2.8 <= mag < 3.0           -> staff only
    Outside Tbilisi, mag < 2.8:
        acceleration at Tbilisi >= M2.8 in Tbilisi -> everyone
        otherwise                                  -> nobody

Abroad:
    acceleration at Georgian border >= M3.0 in Georgia -> everyone
    within 100 km of the border and mag >= 3.0         -> staff only
    otherwise                                          -> nobody

"Acceleration" rules compare how strongly the event would be felt at a place
(Tbilisi, or the nearest point of the Georgian border) against a reference
event: an earthquake of the threshold magnitude located right at that place
(distance 0, depth 0). If the real event shakes the place at least as hard as
the reference would, it is treated as if it had reached the threshold.

The `reason` texts are Georgian because they are read by the duty staff in the logs.
"""

from dataclasses import dataclass
from enum import StrEnum

from .acceleration import estimate_acceleration
from .location import GEORGIA, TBILISI, LocationService

# Magnitude from which an event inside Georgia goes to everyone.
MIN_GEORGIA_MAGNITUDE = 3.0
# Magnitude from which an event inside Tbilisi goes to everyone.
MIN_TBILISI_MAGNITUDE = 2.8
# Magnitude from which an event in Georgia outside Tbilisi goes to staff.
MIN_STAFF_MAGNITUDE = 2.8
# Events abroad closer than this to the border may still go to staff.
ABROAD_STAFF_MAX_DISTANCE_KM = 100


class Audience(StrEnum):
    """Recipient group. Values match the strings used in logs and `to_dict()`."""

    ALL = "all"  # staff and external recipients
    STAFF = "staff"  # institute staff only


@dataclass(frozen=True)
class Decision:
    """Outcome of the rules.

    Attributes:
        audience: Who is notified, or None when nobody is.
        reason: Georgian explanation of the outcome, including the numbers
            it was based on. Always set.
        location_ge: Georgian location text for the notification. Only built
            when something is sent, because it costs extra database lookups.
    """

    audience: Audience | None
    reason: str
    location_ge: str | None = None

    @property
    def send(self) -> bool:
        return self.audience is not None

    @property
    def publish(self) -> bool:
        """Staff-only events are never published to the public site."""
        return self.audience is Audience.ALL


def decide(
    locations: LocationService,
    lat: float,
    lon: float,
    depth_km: float,
    magnitude: float,
) -> Decision:
    """Apply the rules in the module docstring to one earthquake."""
    if locations.is_inside(lat, lon, GEORGIA):
        return _decide_in_georgia(locations, lat, lon, depth_km, magnitude)
    return _decide_abroad(locations, lat, lon, depth_km, magnitude)


def _decide_in_georgia(locations, lat, lon, depth_km, magnitude) -> Decision:
    prefix = "საქართველო."

    # Strong enough anywhere in Georgia.
    if magnitude >= MIN_GEORGIA_MAGNITUDE:
        return Decision(
            Audience.ALL,
            f"ეპიცენტრი საქართველოშია და მაგნიტუდა {magnitude} ≥ {MIN_GEORGIA_MAGNITUDE}",
            prefix + locations.describe_nearest_city(lat, lon),
        )

    # Inside Tbilisi a lower threshold applies.
    if locations.is_inside(lat, lon, TBILISI):
        if magnitude >= MIN_TBILISI_MAGNITUDE:
            return Decision(
                Audience.ALL,
                f"ეპიცენტრი თბილისშია და მაგნიტუდა {magnitude} ≥ {MIN_TBILISI_MAGNITUDE}",
                prefix + locations.describe_relative_to_tbilisi(lat, lon, 0),
            )
        return Decision(
            None,
            f"ეპიცენტრი თბილისშია და მაგნიტუდა {magnitude} < {MIN_TBILISI_MAGNITUDE}",
        )

    # Elsewhere in Georgia: below 3.0 the decision depends on Tbilisi.
    tbilisi_distance = locations.distance_to_border_km(lat, lon, TBILISI)
    where = f"ეპიცენტრი საქართველოშია, თბილისის გარეთ (თბილისიდან {tbilisi_distance} კმ)"

    if magnitude >= MIN_STAFF_MAGNITUDE:
        audience = Audience.STAFF
        reason = (
            f"{where} და მაგნიტუდა {MIN_STAFF_MAGNITUDE} ≤ {magnitude} < {MIN_GEORGIA_MAGNITUDE}, "
            "ამიტომ მხოლოდ თანამშრომლებს"
        )
    else:
        # Would Tbilisi feel this at least as much as an M2.8 inside Tbilisi?
        acceleration = estimate_acceleration(magnitude, tbilisi_distance, depth_km)
        reference = estimate_acceleration(MIN_TBILISI_MAGNITUDE, 0, 0)
        comparison = (
            f"აჩქარება თბილისთან {acceleration:.6g}, თბილისში მომხდარი "
            f"M{MIN_TBILISI_MAGNITUDE}-ის აჩქარება {reference:.6g}"
        )
        if acceleration < reference:
            return Decision(
                None,
                f"{where}, მაგნიტუდა {magnitude} < {MIN_STAFF_MAGNITUDE} და {comparison} — ნაკლებია",
            )
        audience = Audience.ALL
        reason = f"{where}, მაგნიტუდა {magnitude} < {MIN_STAFF_MAGNITUDE}, მაგრამ {comparison} — მეტია ან ტოლი"

    location = prefix + locations.describe_relative_to_tbilisi(lat, lon, tbilisi_distance)
    return Decision(audience, reason, location)


def _decide_abroad(locations, lat, lon, depth_km, magnitude) -> Decision:
    # Would the Georgian border feel this at least as much as an M3.0 inside Georgia?
    border_distance = locations.distance_to_border_km(lat, lon, GEORGIA)
    acceleration = estimate_acceleration(magnitude, border_distance, depth_km)
    reference = estimate_acceleration(MIN_GEORGIA_MAGNITUDE, 0, 0)
    strong_enough = acceleration >= reference
    # Fallback for staff: close to the border and itself at least M3.0.
    close_enough = (
        border_distance <= ABROAD_STAFF_MAX_DISTANCE_KM and magnitude >= MIN_GEORGIA_MAGNITUDE
    )

    where = f"ეპიცენტრი საქართველოს საზღვარს გარეთაა (საზღვრიდან {border_distance} კმ)"
    comparison = (
        f"აჩქარება საზღვართან {acceleration:.6g}, საქართველოში მომხდარი "
        f"M{MIN_GEORGIA_MAGNITUDE}-ის აჩქარება {reference:.6g}"
    )

    if strong_enough:
        audience = Audience.ALL
        reason = f"{where} და {comparison} — მეტია ან ტოლი"
    elif close_enough:
        audience = Audience.STAFF
        reason = (
            f"{where}, {comparison} — ნაკლებია, მაგრამ საზღვრიდან ≤ {ABROAD_STAFF_MAX_DISTANCE_KM} კმ "
            f"და მაგნიტუდა {magnitude} ≥ {MIN_GEORGIA_MAGNITUDE}, ამიტომ მხოლოდ თანამშრომლებს"
        )
    else:
        return Decision(
            None,
            f"{where}, {comparison} — ნაკლებია, და არ სრულდება პირობა "
            f"„საზღვრიდან ≤ {ABROAD_STAFF_MAX_DISTANCE_KM} კმ და მაგნიტუდა ≥ {MIN_GEORGIA_MAGNITUDE}“",
        )

    location = locations.describe_neighbour_country(lat, lon, border_distance)
    location += locations.describe_nearest_city(lat, lon)
    return Decision(audience, reason, location)
