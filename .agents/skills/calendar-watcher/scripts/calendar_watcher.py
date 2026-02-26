from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.base_watcher import BaseWatcher
from src.core.config import get_env


class CalendarWatcher(BaseWatcher):
    def __init__(self):
        super().__init__(watcher_name="calendar-watcher", check_interval=300)
        token_path = get_env("GOOGLE_CALENDAR_TOKEN_PATH")
        self.calendar_id = get_env("CALENDAR_ID", required=False, default="primary")
        self.creds = Credentials.from_authorized_user_file(token_path)
        self.service = build("calendar", "v3", credentials=self.creds)

    def check_for_updates(self) -> list:
        state = self.load_state()
        processed_ids = set(state.get("processed_ids", []))
        now = datetime.now(timezone.utc)
        end = now + timedelta(hours=24)
        events_result = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=now.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        return [e for e in events if e.get("id") not in processed_ids]

    def create_action_file(self, event) -> Path:
        start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
        title = event.get("summary", "Untitled Event")
        content = f"""---
type: calendar
event_id: {event.get('id', '')}
title: {title}
start: {start}
status: pending
---

## Event Preparation
- [ ] Review agenda
- [ ] Prepare notes
"""
        filepath = self.needs_action / f"CALENDAR_{event.get('id', 'unknown')}.md"
        filepath.write_text(content)

        state = self.load_state()
        processed_ids = set(state.get("processed_ids", []))
        if event.get("id"):
            processed_ids.add(event["id"])
        self.save_state({"processed_ids": sorted(processed_ids)})
        return filepath


if __name__ == "__main__":
    CalendarWatcher().run()
