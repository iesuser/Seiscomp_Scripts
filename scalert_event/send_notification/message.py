"""Subject and body of the notification email."""

from automate_events import Audience, EventAssessment

# Fixed parts of the notification text.
SHAKEMAP_LINK = "Shakemap: https://shorturl.at/ibvtX"
IES_EVENTS_PAGE = "https://ies.iliauni.edu.ge/?page_id=121"
SIGNATURE = (
    "ილიას სახელმწიფო უნივერსიტეტი\n"
    "დედამიწის შემსწავლელ მეცნიერებათა ინსტიტუტი და სეისმური მონიტორინგის ეროვნული ცენტრი"
)


def build_subject(assessment: EventAssessment) -> str:
    """E.g. "Earthquake - Automatic: 2026-10-07 05:15:03. mag=3.0M"."""
    return f"Earthquake - {_summary(assessment)}"


def build_body(assessment: EventAssessment, latitude: float, longitude: float) -> str:
    """Plain-text notification body.

    Layout (the first line only for staff-only events):

        STAFF ONLY.
        Automatic: <local time>. mag=<value><type>. <location>
        <Google Maps link>
        Shakemap: <link>

        <IES events page>


        <signature>
    """
    lines = []
    if assessment.audience is Audience.STAFF:
        lines.append("STAFF ONLY.")
    lines += [
        f"{_summary(assessment)}. {assessment.location_ge}",
        f"https://www.google.com/maps/place/{round(latitude, 2)},{round(longitude, 2)}",
        SHAKEMAP_LINK,
        "",
        IES_EVENTS_PAGE,
        "",
        "",
        SIGNATURE,
    ]
    return "\n".join(lines)


def build_sms_text(assessment: EventAssessment) -> str:
    """The first lines of the email body, as in the historic SMS alerts.

        STAFF ONLY.
        Automatic: <local time>. mag=<value><type>. <location>
    """
    text = f"{_summary(assessment)}. {assessment.location_ge}"
    if assessment.audience is Audience.STAFF:
        text = "STAFF ONLY.\n" + text
    return text


def _summary(assessment: EventAssessment) -> str:
    """Shared first part of subject and body: "<mode>: <local time>. mag=<value><type>"."""
    local_time = assessment.local_time.strftime("%Y-%m-%d %H:%M:%S")
    return f"{assessment.ev_mode}: {local_time}. mag={assessment.magnitude}{assessment.magnitude_type}"
