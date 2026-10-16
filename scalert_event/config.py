"""Settings for scalert_event, read from `.env` next to this file.

Values already present in the process environment win over `.env`, so a
setting can be overridden for one run, e.g. `DRY_RUN=1 ./scalert_event.py ...`.
"""

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def load_env_file(path: Path = ENV_FILE) -> None:
    """Copy KEY=VALUE lines from `path` into `os.environ` (without overriding).

    Blank lines and lines starting with "#" are ignored; surrounding quotes
    around a value are removed.
    """
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


def _path_setting(name: str, default: Path) -> Path:
    """A path from the environment; relative paths are taken from BASE_DIR."""
    path = Path(os.getenv(name) or default)
    return path if path.is_absolute() else BASE_DIR / path


def _flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class SeiscompDbSettings:
    host: str
    user: str
    password: str
    database: str


@dataclass(frozen=True)
class MailSettings:
    server: str
    port: int
    username: str
    password: str


@dataclass(frozen=True)
class SmsSettings:
    """SMS gateways, tried in `providers` order; a provider without credentials is skipped."""

    providers: tuple[str, ...]
    timeout_s: float
    magti_url: str
    magti_track_url: str
    magti_username: str
    magti_password: str
    magti_client_id: str
    magti_service_id: str
    smsoffice_url: str
    smsoffice_balance_url: str
    smsoffice_key: str
    smsoffice_sender: str
    smsoffice_balance_warning: int
    gsm_url: str
    gsm_code: str


@dataclass(frozen=True)
class RecipientsApiSettings:
    """The iesdata API that holds the recipients managed in the Notify UI."""

    base_url: str
    api_key: str
    # Only needed for a self-signed server certificate; None means the system CA store.
    ca_file: Path | None
    timeout_s: float


@dataclass(frozen=True)
class Settings:
    seiscomp_db: SeiscompDbSettings
    mail: MailSettings
    sms: SmsSettings
    recipients_api: RecipientsApiSettings
    recipients_file: Path
    sms_recipients_file: Path
    send_email: bool
    send_sms: bool
    # Publishable events are also added to the iesdata site (send_eq2api).
    send_eq2api: bool
    log_file: Path
    log_level: str
    dry_run: bool
    # How long to keep retrying while scdb has not yet written the event.
    db_retries: int
    db_retry_delay_s: float


def load_settings() -> Settings:
    """Read `.env` and the environment into a `Settings` object."""
    load_env_file()
    return Settings(
        seiscomp_db=SeiscompDbSettings(
            host=os.getenv("SC_DB_HOST", "127.0.0.1"),
            user=os.getenv("SC_DB_USER", "sysop"),
            password=os.getenv("SC_DB_PASSWORD", ""),
            database=os.getenv("SC_DB_NAME", "seiscomp"),
        ),
        mail=MailSettings(
            server=os.getenv("MAIL_SERVER", ""),
            port=int(os.getenv("MAIL_PORT") or 587),
            username=os.getenv("MAIL_USERNAME", ""),
            password=os.getenv("MAIL_PASSWORD", ""),
        ),
        sms=SmsSettings(
            providers=tuple(
                name.strip().lower()
                for name in os.getenv("SMS_PROVIDERS", "magti,smsoffice,gsm").split(",")
                if name.strip()
            ),
            timeout_s=float(os.getenv("SMS_TIMEOUT") or 10),
            magti_url=os.getenv("MAGTI_URL", "http://81.95.160.47/mt/oneway"),
            magti_track_url=os.getenv("MAGTI_TRACK_URL", "http://81.95.160.47/bi/track.php"),
            magti_username=os.getenv("MAGTI_USERNAME", ""),
            magti_password=os.getenv("MAGTI_PASSWORD", ""),
            magti_client_id=os.getenv("MAGTI_CLIENT_ID", "643"),
            magti_service_id=os.getenv("MAGTI_SERVICE_ID", "1"),
            smsoffice_url=os.getenv("SMSOFFICE_URL", "https://smsoffice.ge/api/v2/send/"),
            smsoffice_balance_url=os.getenv("SMSOFFICE_BALANCE_URL", "https://smsoffice.ge/api/getBalance"),
            smsoffice_key=os.getenv("SMSOFFICE_KEY", ""),
            smsoffice_sender=os.getenv("SMSOFFICE_SENDER", "IES"),
            smsoffice_balance_warning=int(os.getenv("SMSOFFICE_BALANCE_WARNING") or 5000),
            gsm_url=os.getenv("GSM_SMS_URL", "http://iesresource.iliauni.edu.ge/block/ies_gsm_sms_sender.php"),
            gsm_code=os.getenv("GSM_SMS_CODE", ""),
        ),
        recipients_api=RecipientsApiSettings(
            base_url=os.getenv("Recp_Exporter_API_URL", "https://iesdata.iliauni.edu.ge:3030/"),
            api_key=os.getenv("Recp_Exporter_API_KEY", ""),
            ca_file=_path_setting("Recp_Exporter_API_CA", "") if os.getenv("Recp_Exporter_API_CA") else None,
            timeout_s=float(os.getenv("Recp_Exporter_API_TIMEOUT") or 20),
        ),
        recipients_file=_path_setting("RECIPIENTS_FILE", BASE_DIR / "recipients" / "email_recipients.json"),
        sms_recipients_file=_path_setting("SMS_RECIPIENTS_FILE", BASE_DIR / "recipients" / "sms_recipients.json"),
        send_email=_flag("SEND_EMAIL", default=True),
        send_sms=_flag("SEND_SMS", default=True),
        send_eq2api=_flag("SEND_EQ2API", default=True),
        log_file=_path_setting("LOG_FILE", BASE_DIR / "logs" / "event_scalert.log"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        dry_run=_flag("DRY_RUN"),
        db_retries=int(os.getenv("SC_DB_RETRIES") or 5),
        db_retry_delay_s=float(os.getenv("SC_DB_RETRY_DELAY") or 3),
    )
