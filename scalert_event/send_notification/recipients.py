"""Recipients of the notifications, read from the JSON files written by
recipients/update_recipients.py from the iesdata API:

    RECIPIENTS_FILE      recipients/email_recipients.json
    SMS_RECIPIENTS_FILE  recipients/sms_recipients.json

File format (see the *.example.json files next to them):

    [
      {"username": "...", "email": "a@iliauni.edu.ge", "is_staff": true,  "is_active": true},
      {"username": "...", "email": "b@example.com",    "is_staff": false, "is_active": true}
    ]

The SMS file has "phone_number" instead of "email". `is_active` defaults to
true and `is_staff` to false when omitted; other keys are ignored.
"""

import json
import logging
import re
from pathlib import Path

from automate_events import Audience

logger = logging.getLogger(__name__)

# Georgian mobile numbers as the SMS gateways expect them: 995 + 9 digits.
_PHONE_RE = re.compile(r"^995\d{9}$")


class RecipientsError(RuntimeError):
    """A recipients file is missing or malformed."""


def recipient_emails(audience: Audience, path: Path) -> list[str]:
    """Active addresses for `audience`, sorted and without duplicates.

    `Audience.ALL` means staff and external recipients; `Audience.STAFF`
    means recipients marked `is_staff` only.
    """
    return sorted({value.strip() for value in _values(audience, path, "email") if value.strip()})


def recipient_numbers(audience: Audience, path: Path) -> list[str]:
    """Active phone numbers for `audience` as "995XXXXXXXXX", sorted, without duplicates.

    Numbers that cannot be normalized are logged and skipped.
    """
    numbers = set()
    for value in _values(audience, path, "phone_number"):
        number = normalize_phone(value)
        if number:
            numbers.add(number)
        else:
            logger.warning("Skipping invalid phone number %r in %s", value, path)
    return sorted(numbers)


def normalize_phone(value: str) -> str | None:
    """"+995 555 12-34-56", "995555123456" or "555123456" -> "995555123456"; None if invalid."""
    digits = re.sub(r"[\s\-().]", "", str(value or "")).lstrip("+")
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 9 and digits.startswith("5"):
        digits = "995" + digits
    return digits if _PHONE_RE.match(digits) else None


def _values(audience: Audience, path: Path, key: str) -> list[str]:
    """`key` of every active entry in `path` that belongs to `audience`."""
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RecipientsError(f"Recipients file not found: {path}") from None
    except ValueError as exc:
        raise RecipientsError(f"Recipients file is not valid JSON: {path}: {exc}") from None
    if not isinstance(entries, list):
        raise RecipientsError(f"Recipients file must contain a list: {path}")

    values = []
    for entry in entries:
        value = str(entry.get(key) or "")
        if not value or not entry.get("is_active", True):
            continue
        if audience is Audience.STAFF and not entry.get("is_staff", False):
            continue
        values.append(value)
    return values
