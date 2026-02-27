from __future__ import annotations

from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

import schedule as schedule_lib

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


# ─── Scheduling support ─────────────────────────────────────────────────

def _parse_schedule_file(path: Path) -> dict | None:
    """Parse a schedule file frontmatter to extract scheduling params."""
    content = path.read_text(encoding="utf-8", errors="ignore")
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    meta = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            clean_val = val.strip().strip('"').strip("'")
            meta[key.strip()] = clean_val
    meta["body"] = parts[2].strip()
    meta["filename"] = path.name
    return meta


def _trigger_linkedin_draft(vault: Path) -> None:
    """Generate a LinkedIn post draft for approval."""
    try:
        module_file = ROOT / ".agents/skills/linkedin-poster/scripts/linkedin_poster.py"
        spec = importlib.util.spec_from_file_location("linkedin_poster_dynamic", module_file)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load linkedin_poster module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.generate_draft(vault)
        append_dashboard(vault, "Scheduled LinkedIn draft created for approval")
    except Exception as exc:
        append_dashboard(vault, f"Failed to create LinkedIn draft: {exc}")
        log_action(
            action_type="scheduled_task_error",
            target="linkedin_draft",
            parameters={"error": str(exc)},
            result="error",
        )


def _trigger_social_draft(vault: Path, platform: str) -> None:
    try:
        module_file = ROOT / ".agents/skills/social-poster/scripts/social_poster.py"
        spec = importlib.util.spec_from_file_location("social_poster_dynamic", module_file)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load social_poster module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        module.generate_draft(vault, platform=platform)
        append_dashboard(vault, f"Scheduled {platform} draft created for approval")
    except Exception as exc:
        append_dashboard(vault, f"Failed to create {platform} draft: {exc}")
        log_action(
            action_type="scheduled_task_error",
            target=f"{platform}_draft",
            parameters={"error": str(exc)},
            result="error",
        )


def _trigger_ceo_briefing(vault: Path) -> None:
    try:
        module_file = ROOT / ".agents/skills/ceo-briefing/scripts/ceo_briefing.py"
        spec = importlib.util.spec_from_file_location("ceo_briefing_dynamic", module_file)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load ceo_briefing module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        output = module.generate_weekly_briefing(vault)
        append_dashboard(vault, f"Weekly CEO briefing generated: {output.name}")
    except Exception as exc:
        append_dashboard(vault, f"Failed to generate CEO briefing: {exc}")
        log_action(
            action_type="scheduled_task_error",
            target="ceo_briefing",
            parameters={"error": str(exc)},
            result="error",
        )


def load_schedules(vault: Path) -> None:
    """Load schedule files from Vault/Schedules/ and register them."""
    schedules_dir = vault / "Schedules"
    schedules_dir.mkdir(parents=True, exist_ok=True)

    # Clear any previously scheduled jobs
    schedule_lib.clear()

    for sched_file in schedules_dir.glob("*.md"):
        meta = _parse_schedule_file(sched_file)
        if not meta:
            continue

        task_type = meta.get("task", "")
        frequency = meta.get("frequency", "")
        time_str = meta.get("time", "09:00")
        days = meta.get("days", "monday,wednesday,friday")

        if task_type == "linkedin_post":
            day_list = [d.strip().lower() for d in days.split(",")]
            for day in day_list:
                job = getattr(schedule_lib.every(), day, None)
                if job:
                    job.at(time_str).do(_trigger_linkedin_draft, vault)

        elif task_type in {"facebook_post", "instagram_post", "twitter_post"}:
            platform = task_type.replace("_post", "")
            day_list = [d.strip().lower() for d in days.split(",")]
            for day in day_list:
                job = getattr(schedule_lib.every(), day, None)
                if job:
                    job.at(time_str).do(_trigger_social_draft, vault, platform)

        elif task_type == "weekly_ceo_briefing":
            day_list = [d.strip().lower() for d in days.split(",")]
            for day in day_list:
                job = getattr(schedule_lib.every(), day, None)
                if job:
                    job.at(time_str).do(_trigger_ceo_briefing, vault)

        elif task_type == "custom":
            # For future extensibility — create action file from schedule body
            if frequency == "daily":
                schedule_lib.every().day.at(time_str).do(
                    _create_scheduled_action, vault, meta
                )

    # Count registered jobs
    job_count = len(schedule_lib.get_jobs())
    if job_count > 0:
        log_action(
            action_type="schedules_loaded",
            target="orchestrator",
            parameters={"job_count": job_count},
            result="success",
        )


def _create_scheduled_action(vault: Path, meta: dict) -> None:
    """Create an action file from a scheduled task."""
    needs_action = vault / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    action_path = needs_action / f"SCHEDULED_{meta.get('filename', 'task')}_{stamp}.md"
    action_path.write_text(
        f"""---
type: scheduled_task
task: {meta.get('task', 'custom')}
created: {datetime.utcnow().isoformat()}Z
status: pending
---

{meta.get('body', 'Scheduled task — check schedule file for details.')}
"""
    )
    append_dashboard(vault, f"Scheduled task triggered: {meta.get('task', 'custom')}")


def main() -> None:
    vault = get_vault_path()
    pid_file = Path("/tmp/orchestrator.pid")
    pid_file.write_text(str(os.getpid()))

    # Load scheduled tasks
    load_schedules(vault)

    while True:
        # Run due scheduled jobs
        schedule_lib.run_pending()

        process_needs_action(vault)
        process_approved(vault)
        process_rejected(vault)
        time.sleep(5)


if __name__ == "__main__":
    main()
