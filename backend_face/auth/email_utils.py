import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from .storage import get_settings
import logging

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str, company_id: Optional[str] = None, settings_override: Optional[Dict[str, Any]] = None):
    """Send mail using the selected tenant/global SMTP configuration.

    Passwords remain decrypted only inside the backend process. The API never
    needs to send the stored SMTP password back to the frontend.
    """
    settings = settings_override or get_settings(company_id)
    smtp_host = str(settings.get("smtp_host") or "").strip()
    smtp_port = int(settings.get("smtp_port") or 587)
    smtp_user = str(settings.get("smtp_user") or "").strip()
    smtp_password = str(settings.get("smtp_password") or "")
    smtp_use_tls = bool(settings.get("smtp_use_tls", True))
    email_from = str(settings.get("email_from") or smtp_user).strip()

    if not all([smtp_host, smtp_port, smtp_user, smtp_password, to_email]):
        logger.warning("Email settings not configured. Cannot send email.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
        server.ehlo()
        if smtp_use_tls:
            server.starttls()
            server.ehlo()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info("Email sent successfully to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False
