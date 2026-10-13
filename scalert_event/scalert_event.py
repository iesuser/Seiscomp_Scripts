#!/home/sysop/Clone/Seiscomp_Scripts/scalert_event/venv/bin/python
# -*- coding: utf-8 -*-
"""Called by scalert for every new or updated event (`scripts.event` in scalert.cfg).

scalert passes: message, flag (1=new, 0=update), event publicID, arrival count
and, when known, magnitude. Only the event ID is used for the decision; all
event parameters are read from the SeisComP database.

Every call is decided on its own: each recalculation that meets the rules is
sent (email and SMS), so one event can be notified several times as it is updated.

Manual run (no scalert):
    ./scalert_event.py ies2026rudf
    ./scalert_event.py --dry-run ies2026rudf     # decide and log, send nothing

Every step goes to logs/event_scalert.log, one keyword per line:
    RECEIVED   the script was called, with its arguments
    WAITING    the event is not fully in the database yet, retrying
    INPUT      the event data the decision is based on
    SKIPPED    not processed (not a real event / no magnitude)
    DECISION   SEND or NOT SENT, with the Georgian reason
    MAIL ...   email recipients and delivery result
    SMS ...    SMS numbers, per-gateway result and delivery result
    FAILED     an exception, with traceback
"""

import argparse
import logging
import sys

from automate_events import process_event
from config import Settings, load_settings
from seiscomp_db import load_event
from send_notification.ies_mail_sender import send_event_mail
from send_notification.ies_sms_sender import SmsSender, send_event_sms
from send_notification.mailer import Mailer

logger = logging.getLogger("scalert_event")

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_BAD_ARGS = 2


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decide whether to notify about a SeisComP event and send the notification.",
        usage="%(prog)s [--dry-run] EVENT_ID | MESSAGE FLAG EVENT_ID [ARRIVALS [MAGNITUDE]]",
    )
    parser.add_argument("--dry-run", action="store_true", help="decide and log, but send nothing")
    parser.add_argument("args", nargs="+", help=argparse.SUPPRESS)
    ns = parser.parse_args(argv)

    values = ns.args
    if len(values) == 1:
        ns.message, ns.flag, ns.event_id, ns.arrivals, ns.magnitude = "", "", values[0], "", ""
    elif 3 <= len(values) <= 5:
        values = values + [""] * (5 - len(values))
        ns.message, ns.flag, ns.event_id, ns.arrivals, ns.magnitude = values
    else:
        parser.error("expected EVENT_ID, or MESSAGE FLAG EVENT_ID [ARRIVALS [MAGNITUDE]]")
    ns.event_id = ns.event_id.strip()
    if not ns.event_id:
        parser.error("EVENT_ID is empty")
    return ns


def setup_logging(settings: Settings) -> None:
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(settings.log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level, logging.INFO))


def process(event_id: str, settings: Settings, *, dry_run: bool) -> None:
    """Load, decide and (if needed) send for one event. Raises on failure."""
    context = f"event_id={event_id}"
    event = load_event(
        event_id,
        settings.seiscomp_db,
        retries=settings.db_retries,
        retry_delay_s=settings.db_retry_delay_s,
    )
    logger.info(
        "INPUT %s origin=%s origin_time=%s lat=%s lon=%s depth=%s mode=%s type=%s "
        "magnitudes=%s preferred_magnitude=%s",
        context, event.origin_id, event.origin_time, event.latitude, event.longitude,
        event.depth, event.evaluation_mode, event.event_type, event.magnitudes,
        event.preferred_magnitude_type,
    )

    if not event.is_real_event:
        logger.info("SKIPPED %s: event type is '%s'", context, event.event_type)
        return
    if not event.magnitudes:
        logger.info("SKIPPED %s: preferred origin has no magnitudes yet", context)
        return

    result = process_event(
        event.origin_time,
        event.latitude,
        event.longitude,
        event.depth,
        event.evaluation_mode,
        event.magnitudes,
    )

    if not result.send:
        logger.info(
            "DECISION %s NOT SENT magnitude=%s%s local_time=%s reason: %s",
            context, result.magnitude, result.magnitude_type, result.local_time, result.reason,
        )
        return
    logger.info(
        "DECISION %s SEND to=%s publish=%s magnitude=%s%s local_time=%s location=%s reason: %s",
        context, result.audience, result.publish, result.magnitude, result.magnitude_type,
        result.local_time, result.location_ge, result.reason,
    )

    channels = []
    if settings.send_email:
        channels.append(("MAIL", lambda: send_event_mail(
            result,
            event.latitude,
            event.longitude,
            mailer=Mailer(settings.mail),
            recipients_file=settings.recipients_file,
            context=context,
            dry_run=dry_run,
        )))
    if settings.send_sms:
        channels.append(("SMS", lambda: send_event_sms(
            result,
            sender=SmsSender(settings.sms),
            recipients_file=settings.sms_recipients_file,
            context=context,
            dry_run=dry_run,
        )))

    failed = []
    for name, send in channels:
        try:
            send()
        except Exception:
            logger.exception("%s FAILED %s", name, context)
            failed.append(name)
    if failed:
        raise RuntimeError(f"notification channel(s) failed: {', '.join(failed)}")


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        return EXIT_OK if exc.code == 0 else EXIT_BAD_ARGS

    settings = load_settings()
    setup_logging(settings)
    dry_run = args.dry_run or settings.dry_run
    context = f"event_id={args.event_id}"
    logger.info(
        "RECEIVED %s flag=%s arrivals=%s magnitude=%s dry_run=%s message=%r",
        context,
        {"1": "new", "0": "update"}.get(args.flag, args.flag or "-"),
        args.arrivals or "-",
        args.magnitude or "-",
        dry_run,
        args.message,
    )

    try:
        process(args.event_id, settings, dry_run=dry_run)
    except Exception:
        logger.exception("FAILED %s", context)
        return EXIT_FAILED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
