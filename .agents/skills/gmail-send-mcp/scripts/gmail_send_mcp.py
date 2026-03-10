"""Gmail Send MCP Server — exposes send_email, draft_email, list_drafts tools."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import get_env, DRY_RUN, require_local_execution, ZoneViolationError
from src.core.audit_logger import log_action

logger = logging.getLogger("gmail-send-mcp")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

mcp = FastMCP("gmail-send")


def _get_smtp_config() -> dict:
    return {
        'smtp_server': os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        'smtp_port': int(os.getenv("SMTP_PORT", "587")),
        'sender_email': (
            os.getenv("SENDER_EMAIL", "")
            or os.getenv("GMAIL_SENDER", "")
            or os.getenv("GMAIL_DELEGATE_EMAIL", "")
        ),
        'sender_password': os.getenv("SENDER_PASSWORD", ""),
    }


def _smtp_send(cfg: dict, msg: MIMEMultipart) -> None:
    password = (cfg['sender_password'] or "").replace(" ", "").replace("-", "")
    server = smtplib.SMTP(cfg['smtp_server'], cfg['smtp_port'])
    server.starttls()
    server.login(cfg['sender_email'], password)
    server.send_message(msg)
    server.quit()


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via SMTP.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Plain text email body

    Returns:
        Confirmation message or dry-run notice
    """
    try:
        require_local_execution("send_email")
    except ZoneViolationError as exc:
        log_action(
            action_type="email_send",
            target=to,
            parameters={"subject": subject},
            result=f"blocked: {exc}",
        )
        return f"Blocked by zone policy: {exc}"

    if DRY_RUN:
        msg = f"[DRY RUN] Would send email to {to}, subject: {subject}"
        logger.info(msg)
        log_action(
            action_type="email_send",
            target=to,
            parameters={"subject": subject, "dry_run": True},
            result="dry_run",
        )
        return msg

    cfg = _get_smtp_config()
    if not cfg['sender_email'] or not cfg['sender_password']:
        return "Error: SMTP credentials not configured (SENDER_EMAIL / SENDER_PASSWORD)"

    try:
        mime_msg = MIMEMultipart()
        mime_msg['From'] = cfg['sender_email']
        mime_msg['To'] = to
        mime_msg['Subject'] = subject
        mime_msg['Date'] = formatdate(localtime=True)
        mime_msg['Message-ID'] = make_msgid()
        mime_msg.attach(MIMEText(body, 'plain'))

        _smtp_send(cfg, mime_msg)

        log_action(
            action_type="email_send",
            target=to,
            parameters={"subject": subject},
            result="success",
            approval_status="approved",
            approved_by="human",
        )
        return f"Email sent to {to}"
    except smtplib.SMTPAuthenticationError:
        log_action(action_type="email_send", target=to, parameters={"subject": subject}, result="error: auth failed")
        return "Failed to send email: SMTP authentication failed. Check SENDER_EMAIL and SENDER_PASSWORD."
    except Exception as exc:
        log_action(action_type="email_send", target=to, parameters={"subject": subject}, result=f"error: {exc}")
        return f"Failed to send email: {exc}"


@mcp.tool()
def draft_email(to: str, subject: str, body: str) -> str:
    """Save a draft email to Vault/Inbox as a markdown file (no SMTP needed).

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Plain text email body

    Returns:
        Confirmation message with draft file path
    """
    if DRY_RUN:
        msg = f"[DRY RUN] Would create draft to {to}, subject: {subject}"
        logger.info(msg)
        log_action(
            action_type="email_draft",
            target=to,
            parameters={"subject": subject, "dry_run": True},
            result="dry_run",
        )
        return msg

    try:
        from src.core.config import get_vault_path
        from datetime import datetime
        import re

        vault_path = get_vault_path()
        drafts_path = vault_path / "Inbox" / "Drafts"
        drafts_path.mkdir(parents=True, exist_ok=True)

        safe_subject = re.sub(r'[^\w\- ]', '_', subject)[:40].strip()
        timestamp = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y%m%d_%H%M%S")
        filename = f"DRAFT_{timestamp}_{safe_subject}.md"
        filepath = drafts_path / filename

        content = f"""---
type: email_draft
to: {to}
subject: {subject}
created: {datetime.now(ZoneInfo('Asia/Karachi')).isoformat()}
status: draft
---

## To
{to}

## Subject
{subject}

## Body
{body}
"""
        filepath.write_text(content)

        log_action(
            action_type="email_draft",
            target=to,
            parameters={"subject": subject, "draft_file": filename},
            result="success",
        )
        return f"Draft saved: {filepath}"
    except Exception as exc:
        log_action(action_type="email_draft", target=to, parameters={"subject": subject}, result=f"error: {exc}")
        return f"Failed to create draft: {exc}"


@mcp.tool()
def list_drafts(max_results: int = 5) -> str:
    """List recent email drafts saved in Vault/Inbox/Drafts.

    Args:
        max_results: Maximum number of drafts to return (default 5)

    Returns:
        List of recent draft files with subject and recipient
    """
    if DRY_RUN:
        return "[DRY RUN] Would list drafts"

    try:
        import json
        from src.core.config import get_vault_path

        vault_path = get_vault_path()
        drafts_path = vault_path / "Inbox" / "Drafts"
        if not drafts_path.exists():
            return "No drafts found."

        draft_files = sorted(drafts_path.glob("DRAFT_*.md"), reverse=True)[:max_results]
        summaries = []
        for f in draft_files:
            lines = f.read_text().splitlines()
            meta = {}
            for line in lines[1:]:
                if line.strip() == '---':
                    break
                if ':' in line:
                    k, _, v = line.partition(':')
                    meta[k.strip()] = v.strip()
            summaries.append({
                "file": f.name,
                "to": meta.get("to", ""),
                "subject": meta.get("subject", ""),
            })
        return json.dumps(summaries, indent=2)
    except Exception as exc:
        return f"Failed to list drafts: {exc}"


def main():
    """Run the MCP server over STDIO."""
    logger.info("Starting Gmail Send MCP Server (DRY_RUN=%s)", DRY_RUN)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
