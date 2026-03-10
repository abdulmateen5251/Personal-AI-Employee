"""Ralph Wiggum Stop Hook — keeps Qwen Code iterating until all tasks are done.

How it works:
- Qwen Code calls this script after each response (Stop hook).
- We check if there are remaining unprocessed items in Vault/Needs_Action/.
- If YES: we output a continue instruction → Qwen Code keeps going.
- If NO: we exit 0 → Qwen Code stops.

Exit codes (Qwen Code hook spec):
  0 = Stop (task complete, let Qwen Code finish)
  2 = Continue (inject the printed message back into Qwen Code as user input)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ── Resolve project root (hook runs from project root via Qwen Code) ──────────
ROOT = Path(os.environ.get("QWEN_PROJECT_ROOT", str(Path(__file__).resolve().parents[2])))
VAULT = Path(os.environ.get("VAULT_PATH", str(ROOT / "Vault")))

NEEDS_ACTION_DIR = VAULT / "Needs_Action"
DONE_DIR = VAULT / "Done"
LOGS_DIR = VAULT / "Logs"

# Files that signal the Ralph loop is already complete for this session
RALPH_MARKER_PREFIX = "RALPH_COMPLETE_"


def _pending_items() -> list[Path]:
    """Return all unprocessed files under Needs_Action (recursively)."""
    if not NEEDS_ACTION_DIR.exists():
        return []
    items = [
        p for p in NEEDS_ACTION_DIR.rglob("*")
        if p.is_file() and not p.name.startswith(".") and p.suffix in {".md", ".txt", ".json"}
    ]
    return items


def _ralph_complete_markers() -> list[Path]:
    """Check if any RALPH_COMPLETE marker was written to Done/ this session."""
    if not DONE_DIR.exists():
        return []
    return [p for p in DONE_DIR.glob(f"{RALPH_MARKER_PREFIX}*.md")]


def _log_hook_state(status: str, pending: int) -> None:
    """Append hook invocation to today's audit log."""
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOGS_DIR / f"{datetime.now(ZoneInfo('Asia/Karachi')).strftime('%Y-%m-%d')}.json"
        record = {
            "timestamp": datetime.now(ZoneInfo("Asia/Karachi")).isoformat(),
            "actor": "ralph_stop_hook",
            "action": "hook_check",
            "status": status,
            "pending_items": pending,
        }
        entries = []
        if log_file.exists():
            try:
                entries = json.loads(log_file.read_text())
                if not isinstance(entries, list):
                    entries = [entries]
            except Exception:
                entries = []
        entries.append(record)
        log_file.write_text(json.dumps(entries, indent=2))
    except Exception:
        pass  # Never crash Qwen Code because of logging


def main() -> None:
    pending = _pending_items()
    markers = _ralph_complete_markers()

    # If there's a completion marker in Done/ → the agent declared it's done
    if markers:
        _log_hook_state("complete_via_marker", 0)
        sys.exit(0)

    # If there are still pending items → tell Qwen Code to continue
    if pending:
        pending_names = [p.name for p in pending[:5]]
        more = f" (and {len(pending) - 5} more)" if len(pending) > 5 else ""
        continue_message = (
            f"RALPH LOOP: {len(pending)} item(s) still pending in Vault/Needs_Action/. "
            f"Items: {', '.join(pending_names)}{more}. "
            f"Continue processing each item: read → reason → write draft to Pending_Approval/. "
            f"When ALL items are processed, write Vault/Done/RALPH_COMPLETE_<timestamp>.md."
        )
        _log_hook_state("continue", len(pending))
        print(continue_message)
        sys.exit(2)  # exit code 2 = inject message and continue

    # Nothing pending and no marker → all done
    _log_hook_state("complete_empty_queue", 0)
    sys.exit(0)


if __name__ == "__main__":
    main()
