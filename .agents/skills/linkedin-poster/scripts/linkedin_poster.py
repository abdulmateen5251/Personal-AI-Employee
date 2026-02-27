"""LinkedIn Poster — generates drafts from business goals, posts approved content."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import get_env, get_vault_path, DRY_RUN
from src.core.audit_logger import log_action

logger = logging.getLogger("linkedin-poster")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

PID_FILE = Path("/tmp/linkedin-poster.pid")
STATE_FILE_NAME = ".linkedin-poster_state.json"
CHECK_INTERVAL = 60  # seconds between checks


# ─── Token / API helpers ────────────────────────────────────────────────

def _load_token() -> dict:
    token_path = get_env("LINKEDIN_TOKEN_PATH")
    return json.loads(Path(token_path).read_text())


def _get_person_urn() -> str:
    """Get person URN from env or token file."""
    urn = os.getenv("LINKEDIN_PERSON_URN", "")
    if urn:
        return urn
    token_data = _load_token()
    return token_data.get("person_urn", "")


def _post_to_linkedin(text: str) -> dict:
    """Publish a text post to LinkedIn via the Posts API."""
    import requests

    token_data = _load_token()
    access_token = token_data["access_token"]
    person_urn = _get_person_urn()

    if not person_urn:
        raise RuntimeError("LINKEDIN_PERSON_URN not configured and not in token file")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Linkedin-Version": "202602",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    payload = {
        "author": person_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    resp = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()

    # LinkedIn returns 201 with x-restli-id header
    post_id = resp.headers.get("x-restli-id", "unknown")
    return {"post_id": post_id, "status": resp.status_code}


# ─── Draft generation ───────────────────────────────────────────────────

def _read_business_context(vault: Path) -> str:
    """Read business goals and active projects for post context."""
    parts = []
    goals_file = vault / "Business_Goals.md"
    if goals_file.exists():
        parts.append(goals_file.read_text(encoding="utf-8", errors="ignore"))

    active_dir = vault / "Active_Project"
    if active_dir.is_dir():
        for f in active_dir.glob("*.md"):
            parts.append(f.read_text(encoding="utf-8", errors="ignore"))

    return "\n\n".join(parts) if parts else "No business context available."


def generate_draft(vault: Path) -> Path | None:
    """Create a LinkedIn post draft in Pending_Approval for human review."""
    context = _read_business_context(vault)
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d_%H%M%S")

    # Generate a draft post based on business context
    # In production, an LLM would generate this; for now, template-based
    post_lines = []
    post_lines.append("🚀 Exciting progress on our latest project!\n")

    # Extract project info from context
    for line in context.split("\n"):
        stripped = line.strip()
        if stripped.startswith("1.") or stripped.startswith("2.") or stripped.startswith("3."):
            if "Due" in stripped or "Budget" in stripped or "-" in stripped:
                post_lines.append(f"📌 {stripped}")

    post_lines.append("\nWe're building the future of AI-powered business automation.")
    post_lines.append("Stay tuned for updates! 💡\n")
    post_lines.append("#AI #Automation #Business #Innovation #Technology")

    draft_text = "\n".join(post_lines)

    pending = vault / "Pending_Approval"
    pending.mkdir(parents=True, exist_ok=True)
    draft_path = pending / f"LINKEDIN_DRAFT_{stamp}.md"
    draft_path.write_text(
        f"""---
type: linkedin_post
status: pending_approval
created: {now.isoformat()}
action: post_to_linkedin
---

## LinkedIn Post Draft

{draft_text}

---
*Move this file to `/Approved` to publish, or `/Rejected` to discard.*
"""
    )
    logger.info("Created LinkedIn draft: %s", draft_path.name)
    log_action(
        action_type="linkedin_draft_created",
        target="linkedin",
        parameters={"draft_file": draft_path.name},
        result="pending_approval",
    )
    return draft_path


# ─── Approved post processing ───────────────────────────────────────────

def _extract_post_text(content: str) -> str:
    """Extract the actual post text from the draft markdown."""
    lines = content.split("\n")
    in_body = False
    body_lines = []
    for line in lines:
        if line.strip() == "## LinkedIn Post Draft":
            in_body = True
            continue
        if in_body:
            if line.strip().startswith("---"):
                break
            body_lines.append(line)
    text = "\n".join(body_lines).strip()
    return text if text else content


def process_approved_posts(vault: Path) -> None:
    """Check for approved LinkedIn drafts and post them."""
    approved = vault / "Approved"
    done = vault / "Done"
    done.mkdir(parents=True, exist_ok=True)

    if not approved.is_dir():
        return

    for draft_file in approved.glob("LINKEDIN_DRAFT_*.md"):
        content = draft_file.read_text(encoding="utf-8", errors="ignore")

        if "linkedin_post" not in content:
            continue

        post_text = _extract_post_text(content)

        if DRY_RUN:
            logger.info("[DRY RUN] Would post to LinkedIn: %s...", post_text[:80])
            log_action(
                action_type="linkedin_post",
                target="linkedin",
                parameters={"text_preview": post_text[:100], "dry_run": True},
                result="dry_run",
            )
        else:
            try:
                result = _post_to_linkedin(post_text)
                logger.info("Posted to LinkedIn: %s", result)
                log_action(
                    action_type="linkedin_post",
                    target="linkedin",
                    parameters={
                        "post_id": result.get("post_id", ""),
                        "text_preview": post_text[:100],
                    },
                    result="success",
                    approval_status="approved",
                    approved_by="human",
                )
            except Exception as exc:
                logger.error("Failed to post to LinkedIn: %s", exc)
                log_action(
                    action_type="linkedin_post",
                    target="linkedin",
                    parameters={"text_preview": post_text[:100]},
                    result=f"error: {exc}",
                )
                continue

        # Move to Done
        import shutil
        shutil.move(str(draft_file), str(done / draft_file.name))


# ─── State management ───────────────────────────────────────────────────

def _load_state(vault: Path) -> dict:
    state_file = vault / "Logs" / STATE_FILE_NAME
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {"last_draft_time": None, "posts_today": 0, "last_post_date": None}


def _save_state(vault: Path, state: dict) -> None:
    state_file = vault / "Logs" / STATE_FILE_NAME
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2))


# ─── Main loop ──────────────────────────────────────────────────────────

def main() -> None:
    vault = get_vault_path()
    PID_FILE.write_text(str(os.getpid()))
    logger.info("LinkedIn Poster started (DRY_RUN=%s)", DRY_RUN)

    while True:
        try:
            # Process any approved LinkedIn drafts
            process_approved_posts(vault)
        except Exception as exc:
            logger.exception("Error processing approved posts: %s", exc)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
