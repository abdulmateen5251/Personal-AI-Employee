from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.audit_logger import log_action
from src.core.config import get_vault_path


def append_dashboard(vault: Path, message: str) -> None:
    dashboard = vault / "Dashboard.md"
    if not dashboard.exists():
        dashboard.write_text("# Dashboard\n\n## Recent Activity\n")
    content = dashboard.read_text()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"- [{stamp}] {message}\n"
    if "## Recent Activity" not in content:
        content += "\n## Recent Activity\n"
    content += line
    dashboard.write_text(content)


def requires_approval(text: str) -> bool:
    sensitive = ["payment", "send", "invoice", "transfer", "bank"]
    lowered = text.lower()
    return any(word in lowered for word in sensitive)


def create_plan(vault: Path, source_file: Path) -> Path:
    plans = vault / "Plans"
    plans.mkdir(parents=True, exist_ok=True)
    plan_name = f"PLAN_{source_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    plan_path = plans / plan_name
    plan_path.write_text(
        f"""---
created: {datetime.utcnow().isoformat()}Z
status: pending
source: {source_file.name}
---

## Objective
Process `{source_file.name}` and complete required actions.

## Steps
- [x] Read source file
- [ ] Determine if approval is required
- [ ] Execute or queue action
- [ ] Move artifacts to `/Done`
"""
    )
    return plan_path


def create_approval(vault: Path, source_file: Path, reason: str) -> Path:
    pending = vault / "Pending_Approval"
    pending.mkdir(parents=True, exist_ok=True)
    approval_path = pending / f"APPROVAL_{source_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    approval_path.write_text(
        f"""---
type: approval_request
action: review_and_execute
source: {source_file.name}
reason: {reason}
status: pending
---

Move this file to `/Approved` to proceed or `/Rejected` to cancel.
"""
    )
    return approval_path


def process_needs_action(vault: Path) -> None:
    needs_action = vault / "Needs_Action"
    done = vault / "Done"
    done.mkdir(parents=True, exist_ok=True)

    for source_file in needs_action.glob("*.md"):
        content = source_file.read_text(encoding="utf-8", errors="ignore")
        create_plan(vault, source_file)

        if requires_approval(content):
            approval = create_approval(vault, source_file, "Sensitive action detected")
            append_dashboard(vault, f"Approval requested for {source_file.name}")
            log_action(
                action_type="approval_requested",
                target=source_file.name,
                parameters={"approval_file": approval.name},
                result="queued",
                approval_status="pending",
            )
        else:
            append_dashboard(vault, f"Auto-processed {source_file.name}")
            log_action(
                action_type="auto_process",
                target=source_file.name,
                parameters={},
                result="success",
                approval_status="not_required",
            )

        shutil.move(str(source_file), str(done / source_file.name))


def process_approved(vault: Path) -> None:
    approved = vault / "Approved"
    done = vault / "Done"
    for file in approved.glob("*.md"):
        append_dashboard(vault, f"Approved action executed: {file.name}")
        log_action(
            action_type="approved_execution",
            target=file.name,
            parameters={},
            result="success",
            approval_status="approved",
            approved_by="human",
        )
        shutil.move(str(file), str(done / file.name))


def process_rejected(vault: Path) -> None:
    rejected = vault / "Rejected"
    done = vault / "Done"
    for file in rejected.glob("*.md"):
        append_dashboard(vault, f"Rejected action archived: {file.name}")
        log_action(
            action_type="approved_execution",
            target=file.name,
            parameters={},
            result="rejected",
            approval_status="rejected",
            approved_by="human",
        )
        shutil.move(str(file), str(done / file.name))


def main() -> None:
    vault = get_vault_path()
    pid_file = Path("/tmp/orchestrator.pid")
    pid_file.write_text(str(os.getpid()))

    while True:
        process_needs_action(vault)
        process_approved(vault)
        process_rejected(vault)
        time.sleep(5)


if __name__ == "__main__":
    main()
