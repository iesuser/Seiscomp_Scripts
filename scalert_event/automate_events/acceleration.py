"""Empirical ground-motion model used to compare earthquake effects at a site.

The model estimates how strongly the ground shakes at some distance from an
earthquake. The rules never use the value on its own; they only compare two
estimates (a real event against a reference event), so its unit does not matter
for the decisions.
"""

import math

# Pseudo-depth (km) added in quadrature so the distance never reaches zero
# at the epicentre, where the log term would otherwise diverge.
_PSEUDO_DEPTH_KM = 3.0


def hypocentral_distance_km(epicentral_distance_km: float, depth_km: float) -> float:
    """Distance from the hypocentre to the site, including the pseudo-depth term.

    Args:
        epicentral_distance_km: Distance along the surface from the epicentre to the site.
        depth_km: Hypocentre depth.
    """
    return math.sqrt(
        float(depth_km) ** 2 + float(epicentral_distance_km) ** 2 + _PSEUDO_DEPTH_KM**2
    )


def acceleration_at_distance(magnitude: float, hypocentral_distance: float) -> float:
    """Expected peak ground acceleration for a magnitude at a hypocentral distance.

    log10(A) = -4.4983 + 1.3209·M - 0.0656·M² - 0.0041·R - 0.5229·log10(R²)
    The coefficients are the regional attenuation relation used by the
    original alert script.
    """
    log_acceleration = (
        -4.4983
        + 1.3209 * magnitude
        - 0.0656 * magnitude**2
        - 0.0041 * hypocentral_distance
        - 0.5229 * math.log10(hypocentral_distance**2)
    )
    return 10**log_acceleration


def estimate_acceleration(magnitude: float, epicentral_distance_km: float, depth_km: float) -> float:
    """Expected peak ground acceleration at a site.

    Only meaningful for relative comparisons between events; the rules compare
    an event's value against a reference event, never against absolute limits.
    """
    return acceleration_at_distance(
        magnitude, hypocentral_distance_km(epicentral_distance_km, depth_km)
    )
