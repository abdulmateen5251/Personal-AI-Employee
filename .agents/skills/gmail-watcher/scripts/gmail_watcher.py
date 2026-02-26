from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.base_watcher import BaseWatcher
from src.core.config import get_env


class GmailWatcher(BaseWatcher):
    def __init__(self):
        super().__init__(watcher_name="gmail-watcher", check_interval=120)
        token_path = get_env("GMAIL_TOKEN_PATH")
        self.creds = Credentials.from_authorized_user_file(token_path)
        self.service = build("gmail", "v1", credentials=self.creds)

    def check_for_updates(self) -> list:
        state = self.load_state()
        processed_ids = set(state.get("processed_ids", []))
        results = (
            self.service.users()
            .messages()
            .list(userId="me", q="is:unread is:important")
            .execute()
        )
        messages = results.get("messages", [])
        return [m for m in messages if m["id"] not in processed_ids]

    def create_action_file(self, message) -> Path:
        msg = self.service.users().messages().get(userId="me", id=message["id"]).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

        content = f"""---
type: email
from: {headers.get('From', 'Unknown')}
subject: {headers.get('Subject', 'No Subject')}
received: {datetime.now().isoformat()}
priority: high
status: pending
---

## Email Content
{msg.get('snippet', '')}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing
"""
        filepath = self.needs_action / f"EMAIL_{message['id']}.md"
        filepath.write_text(content)

        state = self.load_state()
        processed_ids = set(state.get("processed_ids", []))
        processed_ids.add(message["id"])
        self.save_state({"processed_ids": sorted(processed_ids)})
        return filepath


if __name__ == "__main__":
    GmailWatcher().run()
