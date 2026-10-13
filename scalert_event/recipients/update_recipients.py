#!/home/sysop/Clone/Seiscomp_Scripts/scalert_event/venv/bin/python
# -*- coding: utf-8 -*-
"""Refresh the recipient files from the iesdata API (GET /api/recips/):

    recipients/email_recipients.json   one entry per email address
    recipients/sms_recipients.json     one entry per phone number

Run periodically (e.g. from cron) so notifications follow the recipients
managed in the Notify UI:

    ./recipients/update_recipients.py            # fetch and write the files
    ./recipients/update_recipients.py --dry-run  # fetch and print, write nothing

A file is replaced only after a successful fetch, and never with a list that
has no active entry unless --allow-empty is given: if the API is down or
returns nothing, the previous recipients stay in place. Each file is checked
separately. Log: logs/update_recipients.log.

API settings come from `.env`: RECIPIENTS_API_URL, RECIPIENTS_API_KEY,
RECIPIENTS_API_CA (the server's self-signed certificate).
"""

import argparse
import json
import logging
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import BASE_DIR, RecipientsApiSettings, load_settings  # noqa: E402

logger = logging.getLogger("update_recipients")

LOG_FILE = BASE_DIR / "logs" / "update_recipients.log"

EXIT_OK = 0
EXIT_FAILED = 1


class RecipientsApiError(RuntimeError):
    """The API could not be reached or returned an unexpected response."""


def recips_url(base_url: str) -> str:
    """Endpoint URL; RECIPIENTS_API_URL may be the server root or the endpoint itself."""
    base = base_url.rstrip("/")
    if base.endswith("/api/recips"):
        return base + "/"
    return base + "/api/recips/"


def fetch_recips(api: RecipientsApiSettings) -> list[dict]:
    """Return the `items` of GET /api/recips/.

    Raises:
        RecipientsApiError: no API key, HTTP/network/TLS error, or malformed JSON.
    """
    if not api.api_key:
        raise RecipientsApiError("RECIPIENTS_API_KEY is not set")
    request = urllib.request.Request(
        recips_url(api.base_url),
        headers={"Accept": "application/json", "X-API-Key": api.api_key},
        method="GET",
    )
    context = ssl.create_default_context(cafile=api.ca_file if api.ca_file.exists() else None)
    try:
        with urllib.request.urlopen(request, timeout=api.timeout_s, context=context) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RecipientsApiError(f"HTTP {exc.code} from {request.full_url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RecipientsApiError(f"Could not reach {request.full_url}: {exc}") from exc
    except ValueError as exc:
        raise RecipientsApiError(f"Response is not valid JSON: {exc}") from exc

    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise RecipientsApiError("Response has no 'items' list")
    total = payload.get("total")
    if isinstance(total, int) and total > len(items):
        logger.warning("API reports total=%d but returned %d items; the list may be paginated", total, len(items))
    return items


def _flatten(items: list[dict], list_key: str, value_key: str) -> list[dict]:
    """One entry per contact in `recip[list_key]`, keyed by `value_key`.

    A contact is active only if both the recipient and the contact are active.
    """
    entries = []
    for recip in items:
        recip_active = bool(recip.get("is_active", True))
        for contact in recip.get(list_key) or []:
            value = str(contact.get(value_key) or "").strip()
            if not value:
                continue
            entries.append({
                "username": recip.get("username"),
                value_key: value,
                "is_staff": bool(recip.get("is_staff", False)),
                "is_active": recip_active and bool(contact.get("is_active", True)),
            })
    entries.sort(key=lambda entry: (entry[value_key].lower(), str(entry["username"])))
    return entries


def to_email_recipients(items: list[dict]) -> list[dict]:
    """Entries for email_recipients.json, the format read by send_notification.recipients."""
    return _flatten(items, "emails", "email")


def to_sms_recipients(items: list[dict]) -> list[dict]:
    """Entries for sms_recipients.json: {"username", "phone_number", "is_staff", "is_active"}."""
    return _flatten(items, "numbers", "phone_number")


def write_atomically(path: Path, entries: list[dict]) -> bool:
    """Write `entries` to `path` via a temporary file. Returns False if nothing changed."""
    text = json.dumps(entries, ensure_ascii=False, indent=1) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return True


def update_file(name: str, path: Path, entries: list[dict], *, dry_run: bool, allow_empty: bool) -> bool:
    """Write one recipients file and log the outcome. Returns False if it was refused."""
    active = sum(entry["is_active"] for entry in entries)
    staff = sum(entry["is_active"] and entry["is_staff"] for entry in entries)
    summary = f"{name} entries={len(entries)} active={active} active_staff={staff}"

    if dry_run:
        print(f"--- {path}")
        print(json.dumps(entries, ensure_ascii=False, indent=1))
        logger.info("DRY RUN %s, nothing written", summary)
        return True
    if not active and not allow_empty:
        logger.error("FAILED %s: API returned no active entries; keeping previous %s", summary, path)
        return False
    if write_atomically(path, entries):
        logger.info("UPDATED %s %s", path, summary)
    else:
        logger.info("UNCHANGED %s", summary)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh email_recipients.json and sms_recipients.json from the iesdata API."
    )
    parser.add_argument("--dry-run", action="store_true", help="print the result, write nothing")
    parser.add_argument("--allow-empty", action="store_true", help="write a file even if it has no active entry")
    args = parser.parse_args(argv)

    settings = load_settings()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
    )

    try:
        items = fetch_recips(settings.recipients_api)
    except RecipientsApiError as exc:
        logger.error("FAILED keeping previous recipient files: %s", exc)
        return EXIT_FAILED

    # Each file is handled on its own: an empty SMS list does not block the email update.
    results = [
        update_file("email", settings.recipients_file, to_email_recipients(items),
                    dry_run=args.dry_run, allow_empty=args.allow_empty),
        update_file("sms", settings.sms_recipients_file, to_sms_recipients(items),
                    dry_run=args.dry_run, allow_empty=args.allow_empty),
    ]
    return EXIT_OK if all(results) else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
