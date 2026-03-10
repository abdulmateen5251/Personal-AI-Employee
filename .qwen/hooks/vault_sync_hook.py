"""Vault Sync Hook — runs after Qwen Code writes a file.

Updates Dashboard.md with a timestamp entry whenever Qwen Code
creates or modifies a file inside the Vault.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT = Path(os.environ.get("QWEN_PROJECT_ROOT", str(Path(__file__).resolve().parents[2])))
VAULT = Path(os.environ.get("VAULT_PATH", str(ROOT / "Vault")))


def _append_dashboard(message: str) -> None:
    dashboard = VAULT / "Dashboard.md"
    if not dashboard.exists():
        return
    stamp = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y-%m-%d %H:%M")
    line = f"- [{stamp}] {message}\n"
    content = dashboard.read_text()
    dashboard.write_text(content + line)


def main() -> None:
    # Qwen Code may pass tool call info via stdin as JSON
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        tool = data.get("tool_name", "file_op")
        path = data.get("path", "")
        if path and VAULT.name in path:
            _append_dashboard(f"Qwen Code [{tool}] → {Path(path).name}")
    except Exception:
        pass  # Never crash Qwen Code
    sys.exit(0)


if __name__ == "__main__":
    main()
