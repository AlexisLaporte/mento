"""Email notifications via Resend."""

import logging
import os

import resend

log = logging.getLogger(__name__)

BASE_URL = os.getenv('MEMENTO_BASE_URL', 'https://memento.otomata.tech')


def _init():
    key = os.getenv('RESEND_API_KEY')
    if not key:
        return False
    resend.api_key = key
    return True


def send_invite_email(to_email: str, to_name: str, project_title: str,
                      project_slug: str, invited_by: str):
    """Send an invitation email. Silently skips if Resend is not configured."""
    if not _init():
        log.warning("RESEND_API_KEY not set — skipping invitation email to %s", to_email)
        return

    project_url = f"{BASE_URL}/{project_slug}/"
    from_email = os.getenv('RESEND_FROM_EMAIL', 'noreply@otomata.tech')

    resend.Emails.send({
        "from": f"Memento <{from_email}>",
        "to": [to_email],
        "subject": f"You've been invited to {project_title} on Memento",
        "html": f"""
        <div style="font-family: -apple-system, system-ui, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 0;">
            <h2 style="color: #374151; font-size: 18px; margin-bottom: 8px;">You're invited to {project_title}</h2>
            <p style="color: #6b7280; font-size: 14px; line-height: 1.6;">
                {invited_by} has invited you to access the <strong>{project_title}</strong> documentation on Memento.
            </p>
            <a href="{project_url}"
               style="display: inline-block; margin-top: 16px; padding: 10px 24px; background: #6366f1;
                      color: #fff; border-radius: 6px; text-decoration: none; font-size: 14px;">
                Open {project_title}
            </a>
            <p style="color: #9ca3af; font-size: 12px; margin-top: 24px;">
                You'll be asked to sign in with your email address ({to_email}).
            </p>
        </div>
        """,
    })
