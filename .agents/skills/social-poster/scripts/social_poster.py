from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.audit_logger import log_action
from src.core.config import DRY_RUN, get_env, get_vault_path

PID_FILE = Path("/tmp/social-poster.pid")
CHECK_INTERVAL = 30


def _token_for_platform(platform: str) -> str:
    env_map = {
        "facebook": "FACEBOOK_ACCESS_TOKEN",
        "instagram": "INSTAGRAM_ACCESS_TOKEN",
        "twitter": "TWITTER_BEARER_TOKEN",
    }
    key = env_map.get(platform, "")
    return os.getenv(key, "") if key else ""


def generate_draft(vault: Path, platform: str) -> Path:
    pending = vault / "Pending_Approval"
    pending.mkdir(parents=True, exist_ok=True)

    goals = vault / "Business_Goals.md"
    context = goals.read_text(encoding="utf-8", errors="ignore") if goals.exists() else ""
    first_goal = next((line.strip() for line in context.splitlines() if line.strip().startswith("-")), "Build momentum this week")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"SOCIAL_DRAFT_{platform}_{stamp}.md"
    draft_path = pending / filename
    draft_path.write_text(
        f"""---
type: social_post
platform: {platform}
status: pending_approval
action: publish_social
created: {datetime.now(timezone.utc).isoformat()}
---

## Post Content

{first_goal}\n
We are building practical AI automation for real businesses. Follow for weekly updates.

#AI #Automation #Business #BuildInPublic

---
Move this file to `/Approved` to publish or `/Rejected` to discard.
"""
    )
    log_action(
        action_type="social_draft_created",
        target=platform,
        parameters={"draft_file": filename},
        result="pending_approval",
    )
    return draft_path


def _extract_post_text(content: str) -> str:
    marker = "## Post Content"
    if marker not in content:
        return content.strip()
    part = content.split(marker, 1)[1]
    return part.split("---", 1)[0].strip()


def _append_daily_summary(vault: Path, platform: str, preview: str, status: str) -> None:
    briefings = vault / "Briefings"
    briefings.mkdir(parents=True, exist_ok=True)
    path = briefings / f"{datetime.now().strftime('%Y-%m-%d')}_Social_Posting_Summary.md"
    if not path.exists():
        path.write_text("# Social Posting Summary\n\n")
    line = f"- [{datetime.now().strftime('%H:%M')}] {platform}: {status} — {preview[:80]}\n"
    path.write_text(path.read_text() + line)


def _publish(platform: str, text: str) -> dict:
    token = _token_for_platform(platform)
    if DRY_RUN:
        return {"status": "dry_run", "message": f"Would publish to {platform}", "preview": text[:120]}
    if not token:
        raise RuntimeError(f"Missing token for {platform}")
    return {"status": "posted", "platform": platform, "preview": text[:120]}


def process_approved(vault: Path) -> None:
    approved = vault / "Approved"
    done = vault / "Done"
    done.mkdir(parents=True, exist_ok=True)

    for f in approved.glob("SOCIAL_DRAFT_*.md"):
        content = f.read_text(encoding="utf-8", errors="ignore")
        platform = "unknown"
        for line in content.splitlines():
            if line.startswith("platform:"):
                platform = line.split(":", 1)[1].strip()
                break
        text = _extract_post_text(content)

        try:
            result = _publish(platform, text)
            log_action(
                action_type="social_publish",
                target=platform,
                parameters={"file": f.name, "preview": text[:120]},
                result=result.get("status", "unknown"),
                approval_status="approved",
                approved_by="human",
            )
            _append_daily_summary(vault, platform, text, result.get("status", "unknown"))
            shutil.move(str(f), str(done / f.name))
        except Exception as exc:
            log_action(
                action_type="social_publish",
                target=platform,
                parameters={"file": f.name},
                result=f"error: {exc}",
            )


def main() -> None:
    vault = get_vault_path()
    PID_FILE.write_text(str(os.getpid()))
    while True:
        process_approved(vault)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
