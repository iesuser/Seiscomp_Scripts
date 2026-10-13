"""Plain SMTP (STARTTLS) mail delivery."""

import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import MailSettings

logger = logging.getLogger(__name__)


class Mailer:
    def __init__(self, settings: MailSettings):
        self.settings = settings

    def send_mail(self, emails, subject, message, email_type="plain", attachments=None, hide_recipients=False):
        """Send one message. Returns True when the SMTP server accepted it.

        Args:
            emails: One address or a list of addresses.
            subject: Mail subject.
            message: Mail text.
            email_type: "plain" or "html".
            attachments: One file path or a list of paths; missing files are skipped.
            hide_recipients: When True, recipients do not see each other's
                addresses (the visible "To" is the sender, like Bcc).

        SMTP errors are logged with a traceback, not raised.
        """
        recipients = [emails] if isinstance(emails, str) else list(emails or [])
        if not recipients:
            logger.warning("Send mail skipped: recipients list is empty")
            return False
        sender = self.settings.username

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = sender if hide_recipients else ",".join(map(str, recipients))
        msg["Subject"] = subject
        msg.attach(MIMEText(message, email_type))

        attachment_paths = [attachments] if isinstance(attachments, str) else list(attachments or [])
        for file_path in attachment_paths:
            if not os.path.exists(file_path):
                logger.warning("Attachment file not found: %s", file_path)
                continue
            with open(file_path, "rb") as f:
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}")
            msg.attach(attachment)

        try:
            with smtplib.SMTP(host=self.settings.server, port=self.settings.port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.login(sender, self.settings.password)
                server.sendmail(sender, recipients, msg.as_string())
            return True
        except Exception:
            logger.exception("Send mail failed")
            return False
