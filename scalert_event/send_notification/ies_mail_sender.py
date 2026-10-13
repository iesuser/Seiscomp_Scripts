"""Email delivery of automatic earthquake notifications.

Combines the message text (`message`), the recipients (`recipients`) and SMTP
(`mailer`), and logs each step with a MAIL ... keyword.
"""

import logging
from pathlib import Path

from automate_events import EventAssessment

from .mailer import Mailer
from .message import build_body, build_subject
from .recipients import recipient_emails

logger = logging.getLogger(__name__)


def send_event_mail(
    assessment: EventAssessment,
    latitude: float,
    longitude: float,
    *,
    mailer: Mailer,
    recipients_file: Path,
    context: str = "",
    dry_run: bool = False,
) -> bool:
    """Email the event to its audience. Returns True only if the mail was handed to SMTP.

    One message is sent to all recipients with their addresses hidden from each
    other. Nothing is sent when the assessment says not to, or when the
    audience has no active addresses.

    Args:
        assessment: Result of `process_event`.
        latitude, longitude: Epicentre, used for the Google Maps link.
        mailer: SMTP sender.
        recipients_file: JSON list of recipients (see `recipients.py`).
        context: Identifies the event in log lines, e.g. "event_id=...".
        dry_run: Log what would be sent, but send nothing (returns False).

    Raises:
        RecipientsError: the recipients file is missing or malformed.
    """
    if not assessment.send:
        return False

    recipients = recipient_emails(assessment.audience, recipients_file)
    if not recipients:
        logger.warning("MAIL NOT SENT %s audience=%s: no active email recipients", context, assessment.audience)
        return False

    subject = build_subject(assessment)
    body = build_body(assessment, latitude, longitude)
    logger.info(
        "MAIL SENDING %s audience=%s count=%d recipients=%s subject=%r",
        context, assessment.audience, len(recipients), ", ".join(recipients), subject,
    )
    if dry_run:
        logger.info("MAIL DRY RUN %s: nothing sent. Body:\n%s", context, body)
        return False

    sent = mailer.send_mail(recipients, subject, body, hide_recipients=True)
    if sent:
        logger.info("MAIL SENT %s audience=%s count=%d", context, assessment.audience, len(recipients))
    else:
        logger.error(
            "MAIL FAILED %s audience=%s count=%d (SMTP traceback above)",
            context, assessment.audience, len(recipients),
        )
    return sent
