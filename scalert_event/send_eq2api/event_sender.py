"""Publishing automatic earthquakes on the iesdata site.

Turns a SeisComP event and its assessment into the site's event format
(`build_event_payload`) and hands it to `EventApiClient`, logging each step
with an API ... keyword. Both decisions come from the rules:

    send_api         the event is added to (or updated on) the site
    publish_iliauni  it is then also published (or updated) on WordPress; when
                     False, an event published by an earlier calculation is
                     removed from WordPress again
"""

import logging

from automate_events import EventAssessment
from seiscomp_db import EventData

from .send_eq2api import SITE_MAGNITUDE_CODES, EventApiClient

logger = logging.getLogger(__name__)

# SeisComP magnitude types whose upper-case form is not their site code; the
# rest are matched case-insensitively ("MLv" -> "MLV"). "mB" (broadband
# body-wave) is a different magnitude from "mb", so it must not become "MB".
SEISCOMP_MAGNITUDE_ALIASES = {"Ms_20": "MS", "mB": None}

# Rounding of what is sent; SeisComP stores far more digits than are meaningful.
MAGNITUDE_DECIMALS = 3
COORDINATE_DECIMALS = 5
DEPTH_DECIMALS = 3


def site_magnitudes(magnitudes: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    """SeisComP magnitudes keyed by site code and rounded, plus the SeisComP types left out.

    Example: {"MLv": 2.2257, "Mwp": 3.1} -> ({"MLV": 2.226}, ["Mwp"])
    """
    result, skipped = {}, []
    for mag_type, value in magnitudes.items():
        code = SEISCOMP_MAGNITUDE_ALIASES.get(mag_type, mag_type.upper())
        if code in SITE_MAGNITUDE_CODES and code not in result:
            result[code] = round(value, MAGNITUDE_DECIMALS)
        else:
            skipped.append(mag_type)
    return result, skipped


def build_event_payload(event: EventData, assessment: EventAssessment, magnitudes: dict[str, float]) -> dict:
    """The site's event dict (see `send_eq2api`) for a SeisComP event."""
    return {
        "seiscomp_oid": event.event_id,
        "origin_time": event.origin_time.strftime("%Y-%m-%d %H:%M:%S"),
        "latitude": round(event.latitude, COORDINATE_DECIMALS),
        "longitude": round(event.longitude, COORDINATE_DECIMALS),
        "depth": round(event.depth, DEPTH_DECIMALS),
        "magnitudes": magnitudes,
        "location_ge": assessment.location_ge,
        "location_en": assessment.location_en,
        "is_automatic": event.evaluation_mode == "automatic",
    }


def send_event_api(
    event: EventData,
    assessment: EventAssessment,
    *,
    client: EventApiClient,
    context: str = "",
    dry_run: bool = False,
) -> bool:
    """Add the event to the site, or update it there, then publish or unpublish it as the rules say.

    Returns True if the site was changed. If (un)publishing fails, the event stays
    on the site in its previous WordPress state and the error is raised; the next
    recalculation retries.

    Raises:
        ValueError: the payload is invalid (a bug: `build_event_payload` should prevent it).
        EventApiError: the API failed.
    """
    if not assessment.send_api:
        return False

    magnitudes, skipped = site_magnitudes(event.magnitudes)
    if skipped:
        logger.info("API MAGNITUDES SKIPPED %s: unknown to the site: %s", context, ", ".join(skipped))
    if not magnitudes:
        logger.warning("API NOT SENT %s: no magnitude the site knows", context)
        return False

    payload = build_event_payload(event, assessment, magnitudes)
    logger.info("API SENDING %s publish_iliauni=%s payload=%s", context, assessment.publish_iliauni, payload)
    if dry_run:
        logger.info("API DRY RUN %s: nothing sent", context)
        return False

    result = client.add_event(payload)
    logger.info("API %s %s site_id=%s", "CREATED" if result["created"] else "UPDATED", context, result["id"])

    if assessment.publish_iliauni:
        response = client.publish_event(result["id"])
        logger.info(
            "API PUBLISHED %s site_id=%s message=%r wp_response=%r",
            context, result["id"], response.get("message"), response.get("wp_response"),
        )
    elif result["is_published"]:
        response = client.unpublish_event(result["id"])
        logger.info(
            "API UNPUBLISHED %s site_id=%s reason=publish_iliauni=False message=%r wp_response=%r",
            context, result["id"], response.get("message"), response.get("wp_response"),
        )
    return True
