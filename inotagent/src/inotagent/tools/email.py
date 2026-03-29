"""Email tool — send formatted emails via Gmail SMTP."""

from __future__ import annotations

import logging
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SEND_EMAIL_TOOL = {
    "name": "send_email",
    "description": (
        "Send an email with markdown content (converted to HTML). "
        "Restricted to owner email only (OWNER_EMAIL env var)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address. Optional — defaults to owner email if not specified."},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email body in markdown (will be converted to HTML)"},
        },
        "required": ["subject", "body"],
    },
}


def markdown_to_html(md: str) -> str:
    """Convert simple markdown to HTML. Handles headers, bold, italic, code, lists, links."""
    html = md

    # Code blocks (``` ... ```)
    html = re.sub(
        r"```(\w*)\n(.*?)```",
        lambda m: f'<pre style="background:#f4f4f4;padding:12px;border-radius:4px;overflow-x:auto"><code>{m.group(2)}</code></pre>',
        html, flags=re.DOTALL,
    )
    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
    # Headers
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    # Bold and italic
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
    # Links
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)
    # Unordered lists
    html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"(<li>.*?</li>\n?)+", r"<ul>\g<0></ul>", html)
    # Paragraphs (double newline)
    html = re.sub(r"\n\n", "</p><p>", html)
    html = f"<p>{html}</p>"
    # Clean up empty paragraphs
    html = re.sub(r"<p>\s*</p>", "", html)

    return f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; max-width: 700px;">
{html}
<hr style="margin-top: 24px; border: none; border-top: 1px solid #ddd;">
<p style="font-size: 12px; color: #999;">Sent by OpenVAIA agent</p>
</div>"""


class EmailTool:
    """Send emails via Gmail SMTP with whitelist validation."""

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name

    async def send_email(self, subject: str, body: str, to: str = "") -> str:
        """Send an email with markdown body converted to HTML."""
        sender = os.environ.get("GIT_EMAIL", "")
        password = os.environ.get("GMAIL_APP_PASSWORD", "")
        owner_email = os.environ.get("OWNER_EMAIL", "")

        # Default to owner email if not specified
        if not to.strip():
            to = owner_email

        if not sender:
            return "Error: GIT_EMAIL not configured — cannot send email."
        if not password:
            return "Error: GMAIL_APP_PASSWORD not configured — set it in the agent's .env file."
        if not owner_email:
            return "Error: OWNER_EMAIL not configured — set it in the agent's .env file."

        # Whitelist validation
        allowed = {e.strip().lower() for e in owner_email.split(",") if e.strip()}
        if to.strip().lower() not in allowed:
            return f"Error: Email not sent — '{to}' is not in the allowed recipient list."

        # Build email
        msg = MIMEMultipart("alternative")
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject

        # Plain text fallback + HTML version
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(markdown_to_html(body), "html"))

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender, password)
                server.send_message(msg)
            logger.info(f"Email sent to {to}: {subject}")
            return f"Email sent to {to} — subject: {subject}"
        except smtplib.SMTPAuthenticationError:
            return "Error: Gmail authentication failed — check GIT_EMAIL and GMAIL_APP_PASSWORD."
        except Exception as e:
            logger.error(f"Email send failed: {e}", exc_info=True)
            return f"Error: Failed to send email — {e}"
