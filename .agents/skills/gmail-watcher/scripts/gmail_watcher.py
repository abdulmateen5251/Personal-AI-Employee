from __future__ import annotations

import base64
import logging
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.base_watcher import BaseWatcher
from src.core.gmail_auth import build_gmail_service

logger = logging.getLogger("gmail-watcher")


class GmailWatcher(BaseWatcher):
    def __init__(self):
        super().__init__(watcher_name="gmail-watcher", check_interval=120)
        self.service, self.user_id = build_gmail_service()
        # Vault/Inbox — where MD files land
        self.inbox_path = self.vault_path / "Inbox"
        self.inbox_path.mkdir(parents=True, exist_ok=True)

    def check_for_updates(self) -> list:
        state = self.load_state()
        processed_ids = set(state.get("processed_ids", []))
        results = (
            self.service.users()
            .messages()
            .list(userId=self.user_id, q="is:unread", maxResults=20)
            .execute()
        )
        messages = results.get("messages", [])
        return [m for m in messages if m["id"] not in processed_ids]

    def _decode_body(self, payload: dict) -> str:
        """Recursively extract plain-text body from message payload."""
        mime = payload.get("mimeType", "")
        if mime == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            text = self._decode_body(part)
            if text:
                return text
        return ""

    def create_action_file(self, message) -> Path:
        txt = (
            self.service.users()
            .messages()
            .get(userId=self.user_id, id=message["id"], format="full")
            .execute()
        )

        headers = {
            h["name"]: h["value"]
            for h in txt.get("payload", {}).get("headers", [])
        }

        subject  = headers.get("Subject", "(No Subject)")
        from_h   = headers.get("From",    "Unknown")
        date_h   = headers.get("Date",    "")
        snippet  = txt.get("snippet", "")
        body     = self._decode_body(txt.get("payload", {})) or snippet

        content = f"""---
type: email
id: {message['id']}
from: {from_h}
subject: {subject}
date: {date_h}
received: {datetime.now().isoformat()}
status: unread
---

## Subject
{subject}

## From
{from_h}

## Content
{body}

## Snippet
{snippet}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing
"""
        # Write to Vault/Inbox/
        filepath = self.inbox_path / f"EMAIL_{message['id']}.md"
        filepath.write_text(content)
        logger.info("Created inbox file: %s", filepath.name)

        # Mark email as READ so it doesn't process again
        self.service.users().messages().batchModify(
            userId=self.user_id,
            body={"ids": [message["id"]], "removeLabelIds": ["UNREAD"]},
        ).execute()
        logger.info("Marked as read: %s — %s", message["id"], subject)

        # Track processed IDs in state
        state = self.load_state()
        processed_ids = set(state.get("processed_ids", []))
        processed_ids.add(message["id"])
        self.save_state({"processed_ids": sorted(processed_ids)})

        return filepath


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    GmailWatcher().run()

