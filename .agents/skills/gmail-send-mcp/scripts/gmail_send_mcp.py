"""Gmail Send MCP Server — exposes send_email, draft_email, list_drafts tools."""

from __future__ import annotations

import base64
import json
import logging
from email.mime.text import MIMEText
from pathlib import Path
import sys

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import get_env, DRY_RUN
from src.core.audit_logger import log_action

logger = logging.getLogger("gmail-send-mcp")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

mcp = FastMCP("gmail-send")


def _get_gmail_service():
    """Build Gmail API service from saved OAuth token."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_path = get_env("GMAIL_TOKEN_PATH")
    creds = Credentials.from_authorized_user_file(token_path)
    return build("gmail", "v1", credentials=creds)


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Gmail.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Plain text email body

    Returns:
        Confirmation message with message ID or dry-run notice
    """
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

    try:
        service = _get_gmail_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        msg_id = sent.get("id", "unknown")

        log_action(
            action_type="email_send",
            target=to,
            parameters={"subject": subject, "message_id": msg_id},
            result="success",
            approval_status="approved",
            approved_by="human",
        )
        return f"Email sent to {to} (id: {msg_id})"
    except Exception as exc:
        log_action(
            action_type="email_send",
            target=to,
            parameters={"subject": subject},
            result=f"error: {exc}",
        )
        return f"Failed to send email: {exc}"


@mcp.tool()
def draft_email(to: str, subject: str, body: str) -> str:
    """Create a draft email in Gmail.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Plain text email body

    Returns:
        Confirmation message with draft ID
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
        service = _get_gmail_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()
        draft_id = draft.get("id", "unknown")

        log_action(
            action_type="email_draft",
            target=to,
            parameters={"subject": subject, "draft_id": draft_id},
            result="success",
        )
        return f"Draft created for {to} (draft id: {draft_id})"
    except Exception as exc:
        log_action(
            action_type="email_draft",
            target=to,
            parameters={"subject": subject},
            result=f"error: {exc}",
        )
        return f"Failed to create draft: {exc}"


@mcp.tool()
def list_drafts(max_results: int = 5) -> str:
    """List recent email drafts in Gmail.

    Args:
        max_results: Maximum number of drafts to return (default 5)

    Returns:
        JSON-formatted list of recent drafts
    """
    if DRY_RUN:
        return "[DRY RUN] Would list drafts"

    try:
        service = _get_gmail_service()
        results = service.users().drafts().list(
            userId="me", maxResults=max_results
        ).execute()
        drafts = results.get("drafts", [])
        summaries = []
        for d in drafts:
            detail = service.users().drafts().get(userId="me", id=d["id"]).execute()
            headers = {
                h["name"]: h["value"]
                for h in detail.get("message", {}).get("payload", {}).get("headers", [])
            }
            summaries.append({
                "id": d["id"],
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
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
