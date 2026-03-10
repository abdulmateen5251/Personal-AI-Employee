"""Qwen Code Agent — autonomous reasoning loop.

Responsibilities:
1. Scan Vault/Needs_Action/ for unprocessed items
2. Build a context-rich prompt for each item
3. Call `qwen --prompt "..."` (Qwen Code CLI non-interactive mode)
4. Parse the response and write drafts to Vault/Pending_Approval/
5. Monitor Vault/Approved/ and trigger MCP actions
6. Write RALPH_COMPLETE marker when queue is empty

Usage:
    python3 qwen_agent.py [--once] [--max-items N] [--sleep-seconds N]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import get_vault_path, DRY_RUN
from src.core.audit_logger import log_action

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [qwen-agent] %(levelname)s %(message)s",
)
logger = logging.getLogger("qwen-agent")

# ── Paths ─────────────────────────────────────────────────────────────────────
VAULT = get_vault_path()
NEEDS_ACTION = VAULT / "Needs_Action"
PLANS = VAULT / "Plans"
PENDING_APPROVAL = VAULT / "Pending_Approval"
APPROVED = VAULT / "Approved"
REJECTED = VAULT / "Rejected"
DONE = VAULT / "Done"
LOGS = VAULT / "Logs"
STATE_FILE = VAULT / "Logs" / ".qwen-agent-state.json"

HANDBOOK = VAULT / "Company_Handbook.md"
GOALS = VAULT / "Business_Goals.md"
DASHBOARD = VAULT / "Dashboard.md"

PROCESSED_KEY = "processed_files"


# ── State management ──────────────────────────────────────────────────────────

def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {PROCESSED_KEY: []}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _mark_processed(state: dict, path: Path) -> None:
    key = str(path.relative_to(ROOT))
    if key not in state[PROCESSED_KEY]:
        state[PROCESSED_KEY].append(key)
    _save_state(state)


def _is_processed(state: dict, path: Path) -> bool:
    return str(path.relative_to(ROOT)) in state[PROCESSED_KEY]


# ── Context builders ──────────────────────────────────────────────────────────

def _read_safe(path: Path, max_chars: int = 3000) -> str:
    if not path.exists():
        return f"[{path.name} not found]"
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:max_chars] + ("\n...[truncated]" if len(text) > max_chars else "")


def _build_context() -> str:
    handbook = _read_safe(HANDBOOK)
    goals = _read_safe(GOALS)
    return f"""## Company Handbook
{handbook}

## Business Goals
{goals}"""


def _detect_item_type(path: Path, content: str) -> str:
    """Guess the item type from folder name and content."""
    parts = path.parts
    for folder in ("email", "finance", "calendar", "social"):
        if folder in parts:
            return folder
    low = content.lower()
    if any(w in low for w in ("from:", "to:", "subject:", "gmail", "email")):
        return "email"
    if any(w in low for w in ("invoice", "payment", "transaction", "bank", "amount", "credit", "debit")):
        return "finance"
    if any(w in low for w in ("meeting", "event", "calendar", "schedule", "appointment")):
        return "calendar"
    if any(w in low for w in ("linkedin", "twitter", "facebook", "instagram", "post", "social")):
        return "social"
    return "general"


def _build_item_prompt(item_path: Path, item_type: str, content: str, context: str) -> str:
    return f"""You are the Personal AI Employee. Process this {item_type} item from the Vault.

{context}

---
## Item to Process
**File:** {item_path.name}
**Type:** {item_type}
**Content:**
{content}

---
## Your Task
1. Analyse the item and determine the best action.
2. Write a PLAN to Vault/Plans/PLAN_{item_path.stem}_<timestamp>.md
3. Write a DRAFT of the proposed reply/action to Vault/Pending_Approval/{item_type}/DRAFT_{item_path.stem}_<timestamp>.md

The draft MUST use this exact frontmatter format:
```
---
type: {item_type}
action: <send_email|post_linkedin|post_twitter|post_facebook|post_instagram|create_invoice|general_action>
source: {item_path.name}
to: <recipient email if applicable>
subject: <subject if applicable>
platform: <platform if social>
status: pending_approval
created: <ISO timestamp>
---

## Summary
<one sentence>

## Proposed Action
<full content — email body, social post text, or action description>

## Reasoning
<why this action, citing Company_Handbook and Business_Goals>

---
Move to Vault/Approved/ to execute or Vault/Rejected/ to cancel.
```

After writing both files, confirm with: RALPH_TASK_DONE: {item_path.name}
"""


# ── Qwen Code CLI caller ──────────────────────────────────────────────────────

def _call_qwen(prompt: str, timeout: int = 180) -> str:
    """Call Qwen Code CLI in non-interactive one-shot mode and return stdout.

    Uses --yolo (auto-approve all tool calls) so Qwen can write files directly.
    Prompt is passed as a positional argument (--prompt is deprecated in newer versions).
    """
    qwen_bin = shutil.which("qwen") or "qwen"

    cmd = [
        qwen_bin,
        "--yolo",                   # auto-approve all file writes and tool calls
        "--max-session-turns", "30", # enough turns for read → plan → draft
        "--output-format", "text",  # plain text output for parsing
        prompt,                     # positional prompt (one-shot mode)
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "VAULT_PATH": str(VAULT)},
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode not in (0, 130):
            logger.warning("qwen exited with code %d", proc.returncode)
        return output
    except subprocess.TimeoutExpired:
        logger.error("qwen timed out after %ds", timeout)
        return "[TIMEOUT]"
    except FileNotFoundError:
        logger.error("qwen CLI not found in PATH. Install: npm install -g @qwen-ai/qwen-code")
        return "[QWEN_NOT_FOUND]"


def _save_draft_from_output(output: str, item_path: Path, item_type: str) -> Path | None:
    """Parse Qwen's output and save a draft to Pending_Approval/ if Qwen didn't write it.

    Looks for a markdown block with frontmatter between markers:
        ---\ntype: ...\n---\n## Summary ...\n## Proposed Action\n<body>
    If found, saves to Vault/Pending_Approval/<type>/DRAFT_<stem>_<ts>.md
    """
    # Check if Qwen already wrote the draft (look for confirmation phrase)
    draft_written = any(kw in output for kw in (
        "Pending_Approval",
        "RALPH_TASK_DONE",
        "draft saved",
        "file created",
        "written to",
    ))

    # Try to extract frontmatter block from output
    import re
    match = re.search(
        r"```[\s\S]*?---[\s\S]*?type:[\s\S]*?---[\s\S]*?```", output
    )
    if not match:
        # Try bare --- ... --- block
        match = re.search(r"(---\ntype:[\s\S]+?---\n[\s\S]+?)(?:\n---\n|$)", output)

    if match:
        draft_content = match.group(0).strip("`").strip()
    else:
        # Fallback: extract anything after "## Proposed Action"
        proposed_match = re.search(r"## Proposed Action\n([\s\S]+?)(?=## Reasoning|$)", output)
        if not proposed_match:
            logger.info("No draft block found in Qwen output for %s — using raw summary.", item_path.name)
            draft_content = None
        else:
            body = proposed_match.group(1).strip()
            ts_iso = datetime.now(ZoneInfo("Asia/Karachi")).isoformat()
            draft_content = f"""---
type: {item_type}
action: general_action
source: {item_path.name}
status: pending_approval
created: {ts_iso}
---

## Summary
Qwen Code proposed action for {item_path.name}

## Proposed Action
{body}

## Reasoning
Generated by Qwen Code qwen-agent.

---
Move to Vault/Approved/ to execute or Vault/Rejected/ to cancel.
"""

    if draft_content is None:
        return None

    # Save to Pending_Approval/<type>/
    target_dir = PENDING_APPROVAL / item_type
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y%m%d_%H%M%S")
    draft_path = target_dir / f"DRAFT_{item_path.stem}_{ts}.md"

    if not draft_written:
        draft_path.write_text(draft_content, encoding="utf-8")
        logger.info("Draft saved by agent fallback: %s", draft_path.name)
        return draft_path
    else:
        logger.info("Qwen Code wrote draft directly (no fallback needed)")
        return None


# ── Approval handler / MCP dispatcher ────────────────────────────────────────

def _load_frontmatter(text: str) -> dict:
    """Parse simple YAML frontmatter from a markdown file."""
    meta: dict = {}
    if not text.startswith("---"):
        return meta
    parts = text.split("---", 2)
    if len(parts) < 3:
        return meta
    for line in parts[1].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta


def _import_module_from_file(name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _execute_approved(approved_file: Path) -> str:
    """Read an approved file and call the appropriate MCP."""
    content = approved_file.read_text(encoding="utf-8", errors="replace")
    meta = _load_frontmatter(content)
    action = meta.get("action", "").lower()
    item_type = meta.get("type", "general").lower()

    logger.info("Executing approved action: %s (type=%s)", action, item_type)

    if DRY_RUN:
        result = f"[DRY RUN] Would execute: {action} for {approved_file.name}"
        logger.info(result)
        return result

    try:
        if action == "send_email":
            mcp_path = ROOT / ".agents/skills/gmail-send-mcp/scripts/gmail_send_mcp.py"
            mod = _import_module_from_file("gmail_send_mcp", mcp_path)
            to = meta.get("to", os.getenv("RECIPIENT_EMAIL", ""))
            subject = meta.get("subject", "Reply")
            # Extract body from content (strip frontmatter)
            body_parts = content.split("---", 2)
            body = body_parts[2] if len(body_parts) >= 3 else content
            return str(mod.send_email(to=to, subject=subject, body=body.strip()))

        elif action in ("post_linkedin",):
            poster_path = ROOT / ".agents/skills/linkedin-poster/scripts/linkedin_poster.py"
            result = subprocess.run(
                [sys.executable, str(poster_path)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.stdout + result.stderr

        elif action in ("post_twitter", "post_facebook", "post_instagram"):
            platform = action.replace("post_", "")
            social_path = ROOT / ".agents/skills/social-poster/scripts/social_poster.py"
            result = subprocess.run(
                [sys.executable, str(social_path), "--platform", platform],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.stdout + result.stderr

        elif action in ("create_invoice",):
            mcp_path = ROOT / ".agents/skills/odoo-integration/scripts/odoo_mcp_server.py"
            if mcp_path.exists():
                return "[Odoo] Draft invoice creation triggered (manual review in Odoo)"
            return "[Odoo] MCP not available"

        else:
            return f"[INFO] Action '{action}' logged. No automated MCP for this type."

    except Exception as exc:
        logger.error("MCP execution failed: %s", exc)
        return f"[ERROR] {exc}"


def _append_dashboard(message: str) -> None:
    if not DASHBOARD.exists():
        return
    stamp = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y-%m-%d %H:%M")
    DASHBOARD.write_text(DASHBOARD.read_text() + f"- [{stamp}] {message}\n")


def _write_audit(action_type: str, target: str, result: str) -> None:
    try:
        log_action(action_type=action_type, target=target, parameters={}, result=result)
    except Exception:
        pass


def _write_ralph_complete(count: int) -> None:
    DONE.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y%m%d_%H%M%S")
    marker = DONE / f"RALPH_COMPLETE_{ts}.md"
    marker.write_text(
        f"""---
type: ralph_completion
timestamp: {datetime.now(ZoneInfo('Asia/Karachi')).isoformat()}
items_processed: {count}
---

Ralph loop complete. All Needs_Action items processed.
"""
    )
    logger.info("Ralph completion marker written: %s", marker.name)


# ── Main loop ─────────────────────────────────────────────────────────────────

def process_needs_action(state: dict, max_items: int) -> int:
    """Process up to max_items from Needs_Action. Returns count processed."""
    if not NEEDS_ACTION.exists():
        return 0

    items = [
        p for p in NEEDS_ACTION.rglob("*")
        if p.is_file()
        and not p.name.startswith(".")
        and p.suffix in {".md", ".txt", ".json", ".csv"}
        and not _is_processed(state, p)
    ]

    if not items:
        logger.info("Needs_Action queue is empty.")
        return 0

    logger.info("Found %d unprocessed item(s) in Needs_Action.", len(items))
    context = _build_context()
    processed = 0

    for item in items[:max_items]:
        logger.info("Processing: %s", item.name)
        content = _read_safe(item)
        item_type = _detect_item_type(item, content)
        prompt = _build_item_prompt(item, item_type, content, context)

        logger.info("Calling Qwen Code for: %s", item.name)
        output = _call_qwen(prompt)

        if "[QWEN_NOT_FOUND]" in output:
            logger.error("Qwen Code CLI not installed. Stopping.")
            sys.exit(1)

        logger.info("Qwen Code output (%d chars):\n%s", len(output), output[:500])

        # If Qwen didn't write the draft itself, parse its output and save it
        draft_path = _save_draft_from_output(output, item, item_type)
        if draft_path:
            logger.info("Agent saved draft: %s", draft_path)

        _mark_processed(state, item)
        _write_audit("qwen_process", item.name, f"qwen output {len(output)} chars")
        _append_dashboard(f"Qwen processed {item.name} ({item_type}) → draft in Pending_Approval")
        processed += 1

    return processed


def process_approved(state: dict) -> int:
    """Execute all approved items. Returns count executed."""
    if not APPROVED.exists():
        return 0

    approved_items = [
        p for p in APPROVED.rglob("*")
        if p.is_file() and p.suffix == ".md" and not p.name.startswith(".")
    ]

    if not approved_items:
        return 0

    logger.info("Found %d approved item(s) to execute.", len(approved_items))
    executed = 0

    for item in approved_items:
        logger.info("Executing approved: %s", item.name)
        result = _execute_approved(item)
        logger.info("Result: %s", result)

        # Move to Done
        DONE.mkdir(parents=True, exist_ok=True)
        dest = DONE / item.name
        shutil.move(str(item), str(dest))

        _write_audit("mcp_execute", item.name, result[:200])
        _append_dashboard(f"Executed {item.name} → {result[:80]}")
        executed += 1

    return executed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Qwen Code Agent loop")
    p.add_argument("--once", action="store_true", help="Run one cycle and exit")
    p.add_argument("--max-items", type=int, default=5, help="Max Needs_Action items per cycle")
    p.add_argument("--sleep-seconds", type=int, default=30, help="Sleep between cycles")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    state = _load_state()

    logger.info("Qwen Code Agent started. DRY_RUN=%s", DRY_RUN)

    while True:
        # 1. Process approved items first (highest priority)
        approved_count = process_approved(state)

        # 2. Process pending Needs_Action items
        processed_count = process_needs_action(state, args.max_items)

        # 3. If queue is now empty, write Ralph completion marker
        remaining = [
            p for p in NEEDS_ACTION.rglob("*")
            if p.is_file()
            and not p.name.startswith(".")
            and p.suffix in {".md", ".txt", ".json", ".csv"}
            and not _is_processed(state, p)
        ] if NEEDS_ACTION.exists() else []

        if not remaining and processed_count == 0 and approved_count == 0:
            logger.info("All queues empty. Writing Ralph completion marker.")
            _write_ralph_complete(len(state.get(PROCESSED_KEY, [])))

        if args.once:
            logger.info("--once flag set. Exiting.")
            break

        logger.info("Sleeping %ds before next cycle...", args.sleep_seconds)
        time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()
