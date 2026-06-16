"""Gmail sending — ARCHITECTURE PLACEHOLDER, disabled by default.

This MVP prefers copy / manual send. Real sending is intentionally NOT
implemented here. The shape below documents what a safe implementation would
require later (OAuth, approved status, explicit per-send confirmation).

Hard rules:
- Sending stays OFF unless GMAIL_SEND_ENABLED=true.
- No passwords are ever stored. No SMTP password auth.
- Even when enabled, a send requires: status == 'approved' AND
  confirm_send == true, and the action is logged.
"""

from .. import config


class GmailDisabled(Exception):
    """Raised when a send is attempted while Gmail sending is disabled."""


class GmailNotConfigured(Exception):
    """Raised when enabled but OAuth credentials are missing."""


def gmail_enabled() -> bool:
    return config.gmail_send_enabled()


def send_via_gmail(*, to_email: str, subject: str, body: str, confirm_send: bool) -> dict:
    """Placeholder send. Never actually transmits mail in this version.

    Raises GmailDisabled when sending is off (the router converts this to a
    friendly message, not a 500).
    """
    if not gmail_enabled():
        raise GmailDisabled(
            "Gmail sending is disabled. Copy/manual send is available."
        )

    # Enabled path (future): verify OAuth creds exist, but DO NOT send yet.
    if not (config.get_google_client_id() and config.get_google_client_secret()):
        raise GmailNotConfigured(
            "Gmail sending is enabled but OAuth credentials are not configured."
        )

    # Real OAuth + Gmail API send is deliberately not implemented in this MVP.
    raise GmailNotConfigured(
        "Gmail OAuth send is not implemented in this version. Use copy/manual send."
    )
