from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import get_vault_path

PROCESSES = {
    "orchestrator": ["python3", str(ROOT / ".agents/skills/orchestrator/scripts/orchestrator.py")],
    "filesystem-watcher": ["python3", str(ROOT / ".agents/skills/filesystem-watcher/scripts/filesystem_watcher.py")],
    "finance-watcher": ["python3", str(ROOT / ".agents/skills/finance-watcher/scripts/finance_watcher.py")],
    "gmail-watcher": ["python3", str(ROOT / ".agents/skills/gmail-watcher/scripts/gmail_watcher.py")],
    "gmail-send-mcp": ["python3", str(ROOT / ".agents/skills/gmail-send-mcp/scripts/gmail_send_mcp.py")],
    "linkedin-poster": ["python3", str(ROOT / ".agents/skills/linkedin-poster/scripts/linkedin_poster.py")],
    "social-poster": ["python3", str(ROOT / ".agents/skills/social-poster/scripts/social_poster.py")],
    "ceo-briefing": ["python3", str(ROOT / ".agents/skills/ceo-briefing/scripts/ceo_briefing.py")],
    "odoo-mcp": ["python3", str(ROOT / ".agents/skills/odoo-integration/scripts/odoo_mcp_server.py")],
}


def is_process_running(pid_file: Path) -> bool:
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        return Path(f"/proc/{pid}").exists()
    except Exception:
        return False


def notify_human(vault: Path, message: str) -> None:
    alert = vault / "Needs_Action" / f"ALERT_{int(time.time())}.md"
    alert.write_text(
        f"""---
type: system_alert
status: pending
---

{message}
"""
    )


def check_and_restart(vault: Path) -> None:
    for name, cmd in PROCESSES.items():
        pid_file = Path(f"/tmp/{name}.pid")
        if not is_process_running(pid_file):
            proc = subprocess.Popen(cmd, cwd=ROOT)
            pid_file.write_text(str(proc.pid))
            notify_human(vault, f"{name} was restarted")


def main() -> None:
    vault = get_vault_path()
    while True:
        check_and_restart(vault)
        time.sleep(30)


if __name__ == "__main__":
    main()
