from __future__ import annotations

import email
import html
import imaplib
import logging
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from email.header import decode_header
from email.utils import parseaddr
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.base_watcher import BaseWatcher

logger = logging.getLogger("gmail-watcher")


def _get_imap_config() -> dict:
    return {
        'imap_server': os.getenv("IMAP_SERVER", "imap.gmail.com"),
        'imap_port': int(os.getenv("IMAP_PORT", "993")),
        'imap_mailbox': os.getenv("IMAP_MAILBOX", "INBOX"),
        'sender_email': (
            os.getenv("SENDER_EMAIL", "")
            or os.getenv("GMAIL_SENDER", "")
            or os.getenv("GMAIL_DELEGATE_EMAIL", "")
        ),
        'sender_password': os.getenv("SENDER_PASSWORD", ""),
    }


def _decode_mime_header(value: str) -> str:
    if not value:
        return "(no value)"
    decoded_parts = decode_header(value)
    parts = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            parts.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            parts.append(part)
    return "".join(parts)


def _extract_email_content(message) -> str:
    text_parts: list[str] = []
    html_parts: list[str] = []

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            content_disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in content_disposition:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if content_type == "text/plain":
                text_parts.append(decoded)
            elif content_type == "text/html":
                html_parts.append(decoded)
    else:
        payload = message.get_payload(decode=True)
        if payload:
            charset = message.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if message.get_content_type() == "text/html":
                html_parts.append(decoded)
            else:
                text_parts.append(decoded)

    if text_parts:
        return "\n".join(text_parts).strip()
    if html_parts:
        html_content = "\n".join(html_parts)
        no_tags = re.sub(r"<[^>]+>", " ", html_content)
        return html.unescape(re.sub(r"\s+", " ", no_tags)).strip()
    return "(no readable body content)"


class GmailWatcher(BaseWatcher):
    def __init__(self):
        super().__init__(watcher_name="gmail-watcher", check_interval=120)
        self.cfg = _get_imap_config()
        self._password = (self.cfg['sender_password'] or "").replace(" ", "").replace("-", "")
        # Vault/Inbox — where MD files land
        self.inbox_path = self.vault_path / "Inbox"
        self.inbox_path.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> imaplib.IMAP4_SSL:
        mail = imaplib.IMAP4_SSL(self.cfg['imap_server'], self.cfg['imap_port'])
        mail.login(self.cfg['sender_email'], self._password)
        mail.select(self.cfg['imap_mailbox'], readonly=False)
        return mail

    def check_for_updates(self) -> list:
        if not self.cfg['sender_email'] or not self._password:
            logger.warning("IMAP credentials not configured — skipping check")
            return []

        state = self.load_state()
        processed_ids: set = set(state.get("processed_ids", []))

        mail = None
        try:
            mail = self._connect()
            status, data = mail.search(None, 'UNSEEN')
            if status != 'OK':
                logger.warning("IMAP search failed")
                return []

            imap_ids = data[0].split()
            new_items = []
            for imap_id in imap_ids:
                fetch_status, message_data = mail.fetch(imap_id, '(RFC822)')
                if fetch_status != 'OK' or not message_data or not message_data[0]:
                    continue
                raw_email = message_data[0][1]
                msg = email.message_from_bytes(raw_email)
                msg_id = msg.get('Message-ID', imap_id.decode())
                if msg_id not in processed_ids:
                    new_items.append({'imap_id': imap_id, 'msg': msg, 'msg_id': msg_id})
            return new_items
        except imaplib.IMAP4.error as exc:
            logger.error("IMAP error during check: %s", exc)
            return []
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

    def create_action_file(self, item: dict) -> Path:
        msg = item['msg']
        msg_id = item['msg_id']
        imap_id = item['imap_id']

        subject = _decode_mime_header(msg.get('Subject', '(No Subject)'))
        from_h = _decode_mime_header(msg.get('From', 'Unknown'))
        date_h = msg.get('Date', '')
        from_email = parseaddr(from_h)[1]
        snippet = msg.get('snippet', '')
        body = _extract_email_content(msg) or snippet

        content = f"""---
type: email
id: {msg_id}
from: {from_h}
from_email: {from_email}
subject: {subject}
date: {date_h}
received: {datetime.now(ZoneInfo('Asia/Karachi')).isoformat()}
status: unread
---

## Subject
{subject}

## From
{from_h}

## Content
{body}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing
"""
        # Sanitise msg_id for use as filename
        safe_id = re.sub(r'[<>:"/\\|?*]', '_', msg_id)[:80]
        filepath = self.inbox_path / f"EMAIL_{safe_id}.md"
        filepath.write_text(content)
        logger.info("Created inbox file: %s", filepath.name)

        # Mark email as read via IMAP
        try:
            mail = self._connect()
            mail.store(imap_id, '+FLAGS', r'\Seen')
            mail.logout()
            logger.info("Marked as read: %s — %s", msg_id, subject)
        except Exception as exc:
            logger.warning("Could not mark email as read: %s", exc)

        # Track processed ID in state
        state = self.load_state()
        processed_ids = set(state.get("processed_ids", []))
        processed_ids.add(msg_id)
        self.save_state({"processed_ids": sorted(processed_ids)})

        return filepath


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    GmailWatcher().run()



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    GmailWatcher().run()

