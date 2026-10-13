"""SMS delivery of automatic earthquake notifications.

Gateways are tried in SMS_PROVIDERS order (default: magti, smsoffice, gsm);
each one only gets the numbers the previous ones failed to reach:

    magti      Magti one-way gateway; each message is then checked on the
               tracking URL, and anything not confirmed counts as failed.
    smsoffice  smsoffice.ge API, up to 3 attempts per number.
    gsm        the GSM modem behind iesresource.iliauni.edu.ge (one request
               for all remaining numbers; success means the request was accepted).

A gateway whose credentials are not set in `.env` is skipped. Because an
unconfirmed Magti message is passed on to the next gateway, a recipient can
occasionally get the same SMS twice; for alerts that is preferred to missing one.
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from automate_events import EventAssessment
from config import SmsSettings

from .message import build_sms_text
from .recipients import recipient_numbers

logger = logging.getLogger(__name__)

# Magti tracking statuses that mean the message was accepted for delivery
# (Kannel delivery-report codes: 1 delivered, 4 buffered, 8 submitted to SMSC).
MAGTI_OK_STATUSES = frozenset({"1", "4", "8"})
MAGTI_TRACK_DELAY_S = 5

SMSOFFICE_ATTEMPTS = 3
SMSOFFICE_RETRY_DELAY_S = 2
SMSOFFICE_ERRORS = {
    10: "destination შეიცავს არაქართულ ნომრებს",
    20: "ბალანსი არასაკმარისია",
    40: "გასაგზავნი ტექსტი 160 სიმბოლოზე მეტია",
    60: "ბრძანებას აკლია content პარამეტრის მნიშვნელობა",
    70: "ბრძანებას აკლია ნომრები",
    75: "ყველა ნომერი სტოპ სიაშია",
    76: "ყველა ნომერი არასწორი ფორმატითაა მოწოდებული",
    77: "ყველა ნომერი სტოპ სიაშია ან არასწორი ფორმატითაა მოწოდებული",
    80: "key-ს შესაბამისი მომხმარებელი ვერ მოიძებნა",
    110: "sender პარამეტრის მნიშვნელობა გაუგებარია",
    120: "გააქტიურეთ api-ის გამოყენების უფლება პროფილის გვერდზე",
    150: "sender არ იძებნება სისტემაში",
    500: "ბრძანებას აკლია key პარამეტრი",
    600: "ბრძანებას აკლია destination პარამეტრი",
    700: "ბრძანებას აკლია sender პარამეტრი",
    800: "ბრძანებას აკლია content პარამეტრი",
    -100: "დროებითი შეფერხება",
}


def http_request(method: str, url: str, *, params: dict | None = None, data: dict | None = None,
                 timeout: float) -> tuple[int, str]:
    """Send a request and return (status, body). Network errors raise OSError."""
    if params:
        url = f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode(params)}"
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


class SmsSender:
    def __init__(self, settings: SmsSettings, http=http_request, sleep=time.sleep):
        self.settings = settings
        self._http = http
        self._sleep = sleep

    def send(self, message: str, numbers: list[str]) -> list[str]:
        """Send `message` to `numbers`, falling back gateway by gateway.

        Returns the numbers no gateway could reach (empty list = all sent).
        """
        remaining = list(numbers)
        gateways = {"magti": self._send_magti, "smsoffice": self._send_smsoffice, "gsm": self._send_gsm}
        for name in self.settings.providers:
            if not remaining:
                break
            gateway = gateways.get(name)
            if gateway is None:
                logger.warning("SMS unknown provider %r in SMS_PROVIDERS, skipped", name)
                continue
            if not self._configured(name):
                logger.info("SMS provider %s is not configured, skipped", name)
                continue
            failed = gateway(message, remaining)
            logger.info("SMS via %s: sent=%d failed=%d", name, len(remaining) - len(failed), len(failed))
            remaining = failed
        if "smsoffice" in self.settings.providers and self._configured("smsoffice"):
            self.check_smsoffice_balance()
        return remaining

    def _configured(self, name: str) -> bool:
        s = self.settings
        return {
            "magti": bool(s.magti_username and s.magti_password),
            "smsoffice": bool(s.smsoffice_key),
            "gsm": bool(s.gsm_url and s.gsm_code),
        }.get(name, False)

    def _send_magti(self, message: str, numbers: list[str]) -> list[str]:
        s = self.settings
        auth = {
            "username": s.magti_username,
            "password": s.magti_password,
            "client_id": s.magti_client_id,
            "service_id": s.magti_service_id,
        }
        failed, message_ids = [], {}
        for number in numbers:
            try:
                status, text = self._http(
                    "GET", s.magti_url, params={**auth, "to": number, "text": message, "coding": 2},
                    timeout=s.timeout_s,
                )
            except OSError as exc:
                logger.warning("SMS magti %s: request failed: %s", number, exc)
                failed.append(number)
                continue
            if status != 200 or not text.startswith("0000") or "-" not in text:
                logger.warning("SMS magti %s: rejected, status=%s response=%r", number, status, text.strip())
                failed.append(number)
                continue
            message_ids[number] = text.split("-", 1)[1].strip()

        if message_ids:
            self._sleep(MAGTI_TRACK_DELAY_S)
        for number, message_id in message_ids.items():
            try:
                status, text = self._http(
                    "GET", s.magti_track_url, params={**auth, "message_id": message_id}, timeout=s.timeout_s,
                )
            except OSError as exc:
                logger.warning("SMS magti %s: tracking failed: %s", number, exc)
                failed.append(number)
                continue
            if status == 200 and text.strip() in MAGTI_OK_STATUSES:
                logger.info("SMS magti %s: delivered, track status=%s", number, text.strip())
            else:
                logger.warning("SMS magti %s: not confirmed, status=%s track=%r", number, status, text.strip())
                failed.append(number)
        return failed

    def _send_smsoffice(self, message: str, numbers: list[str]) -> list[str]:
        s = self.settings
        remaining = list(numbers)
        for attempt in range(1, SMSOFFICE_ATTEMPTS + 1):
            failed = []
            for number in remaining:
                params = {"key": s.smsoffice_key, "destination": number, "sender": s.smsoffice_sender,
                          "content": message}
                try:
                    status, text = self._http("POST", s.smsoffice_url, params=params, timeout=s.timeout_s)
                    result = json.loads(text) if status == 200 else {}
                except (OSError, ValueError) as exc:
                    logger.warning("SMS smsoffice %s: attempt %d failed: %s", number, attempt, exc)
                    failed.append(number)
                    continue
                if result.get("Success"):
                    logger.info("SMS smsoffice %s: accepted, response=%s", number, result)
                    continue
                code = result.get("ErrorCode")
                logger.warning(
                    "SMS smsoffice %s: attempt %d rejected, status=%s error=%s %s",
                    number, attempt, status, code, SMSOFFICE_ERRORS.get(code, text.strip()),
                )
                failed.append(number)
            remaining = failed
            if not remaining:
                break
            if attempt < SMSOFFICE_ATTEMPTS:
                self._sleep(SMSOFFICE_RETRY_DELAY_S)
        return remaining

    def _send_gsm(self, message: str, numbers: list[str]) -> list[str]:
        s = self.settings
        data = {"code": s.gsm_code, "message": message, "numbers": ",".join(numbers)}
        try:
            status, text = self._http("POST", s.gsm_url, data=data, timeout=s.timeout_s)
        except OSError as exc:
            logger.warning("SMS gsm: request failed: %s", exc)
            return list(numbers)
        if status != 200:
            logger.warning("SMS gsm: rejected, status=%s response=%r", status, text.strip()[:200])
            return list(numbers)
        logger.info("SMS gsm: accepted for %s", ", ".join(numbers))
        return []

    def check_smsoffice_balance(self) -> int | None:
        """Log a warning when the smsoffice balance is at or below SMSOFFICE_BALANCE_WARNING."""
        s = self.settings
        try:
            status, text = self._http("GET", s.smsoffice_balance_url, params={"key": s.smsoffice_key},
                                      timeout=s.timeout_s)
            balance = int(json.loads(text)) if status == 200 else None
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("SMS smsoffice balance check failed: %s", exc)
            return None
        if balance is None:
            logger.warning("SMS smsoffice balance check failed: status=%s", status)
        elif balance <= s.smsoffice_balance_warning:
            logger.warning("SMS BALANCE LOW smsoffice: %d SMS left (warning at %d)",
                           balance, s.smsoffice_balance_warning)
        return balance


def send_event_sms(
    assessment: EventAssessment,
    *,
    sender: SmsSender,
    recipients_file: Path,
    context: str = "",
    dry_run: bool = False,
) -> bool:
    """SMS the event to its audience. Returns True only if every number was reached.

    Raises:
        RecipientsError: the SMS recipients file is missing or malformed.
    """
    if not assessment.send:
        return False

    numbers = recipient_numbers(assessment.audience, recipients_file)
    if not numbers:
        logger.warning("SMS NOT SENT %s audience=%s: no active phone numbers", context, assessment.audience)
        return False

    text = build_sms_text(assessment)
    logger.info(
        "SMS SENDING %s audience=%s count=%d numbers=%s length=%d text=%r",
        context, assessment.audience, len(numbers), ", ".join(numbers), len(text), text,
    )
    if dry_run:
        logger.info("SMS DRY RUN %s: nothing sent", context)
        return False

    failed = sender.send(text, numbers)
    if failed:
        logger.error(
            "SMS FAILED %s audience=%s failed=%d/%d numbers=%s",
            context, assessment.audience, len(failed), len(numbers), ", ".join(failed),
        )
        return False
    logger.info("SMS SENT %s audience=%s count=%d", context, assessment.audience, len(numbers))
    return True
