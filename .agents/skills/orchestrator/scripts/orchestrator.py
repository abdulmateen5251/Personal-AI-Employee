from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sys
import time

import schedule as schedule_lib

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.audit_logger import log_action
from src.core.config import get_vault_path

logger = logging.getLogger("orchestrator")


# ─── Email / Invoice parsing helpers ─────────────────────────────────────

def parse_email_frontmatter(content: str) -> dict:
    """Extract YAML-like frontmatter from an EMAIL markdown file."""
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    meta: dict[str, str] = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip().strip('"').strip("'")
    meta["body"] = parts[2].strip()
    return meta


def extract_invoice_hints(text: str) -> dict:
    """Scan email body for quantity, price, and product description hints."""
    hints: dict = {
        "product_description": "",
        "quantity": 1,
        "unit_price": 0.0,
    }
    # Quantity patterns: "10 bottles", "qty: 5", "quantity 20"
    qty_match = re.search(
        r'(?:qty|quantity)[:\s]*([\d]+)|([\d]+)\s*(?:bottles?|units?|pieces?|pcs|items?|cartons?|liters?|gallons?)',
        text, re.IGNORECASE,
    )
    if qty_match:
        hints["quantity"] = int(qty_match.group(1) or qty_match.group(2))

    # Price patterns: "$500", "PKR 2000", "Rs.1500", "price: 100"
    price_match = re.search(
        r'(?:price|amount|total|cost|PKR|Rs\.?|\$|USD|EUR)\s*[:\s]*([\d,]+(?:\.\d{1,2})?)',
        text, re.IGNORECASE,
    )
    if price_match:
        hints["unit_price"] = float(price_match.group(1).replace(",", ""))

    # Product description: first line that mentions a product-like noun
    for line in text.split("\n"):
        if re.search(r'(?:bottle|water|pet|product|order|item|gallon|liter|carton)', line, re.IGNORECASE):
            hints["product_description"] = line.strip()[:120]
            break

    if not hints["product_description"]:
        hints["product_description"] = "Product/Service (see original email)"

    return hints


def extract_meeting_hints(text: str, meta: dict | None = None) -> dict:
    """Parse meeting date, time, and title from email body/metadata."""
    from dateutil import parser as dateutil_parser

    hints: dict = {
        "title": "",
        "date": "",
        "start_time": "",
        "end_time": "",
        "description": "",
    }

    # Use subject as fallback title
    if meta:
        hints["title"] = meta.get("subject", "Meeting")
    if not hints["title"]:
        hints["title"] = "Meeting"

    combined = text
    if meta:
        combined = meta.get("subject", "") + "\n" + text

    # Try to find a date in common formats
    # Patterns: "March 15, 2026", "15/03/2026", "2026-03-15", "15 Mar 2026"
    date_match = re.search(
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})|'                # 2026-03-15, 2026/03/15
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})|'               # 15/03/2026, 15-03-26
        r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*[\s,]*\d{2,4})|'
        r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}[\s,]*\d{2,4})',
        combined, re.IGNORECASE,
    )
    if date_match:
        raw = date_match.group(0).strip().rstrip(",")
        try:
            parsed = dateutil_parser.parse(raw, fuzzy=True, dayfirst=True)
            hints["date"] = parsed.strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            hints["date"] = raw

    # Try to find times: "10:00 AM", "14:30", "2pm - 3pm", "from 10 to 11"
    time_matches = re.findall(
        r'\b(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)\b',
        combined,
    )
    # Filter out likely non-time numbers (years, etc.)
    valid_times = []
    for t in time_matches:
        t_stripped = t.strip()
        if re.match(r'^\d{4}$', t_stripped):
            continue  # skip years
        if re.search(r'(?:am|pm|\d:\d)', t_stripped, re.IGNORECASE):
            valid_times.append(t_stripped)

    if len(valid_times) >= 2:
        hints["start_time"] = valid_times[0]
        hints["end_time"] = valid_times[1]
    elif len(valid_times) == 1:
        hints["start_time"] = valid_times[0]
        # Default: 1 hour meeting
        try:
            parsed_t = dateutil_parser.parse(valid_times[0], fuzzy=True)
            end_t = parsed_t + __import__("datetime").timedelta(hours=1)
            hints["end_time"] = end_t.strftime("%I:%M %p").lstrip("0")
        except (ValueError, OverflowError):
            hints["end_time"] = ""

    # Fallback: if no date found, use tomorrow
    if not hints["date"]:
        hints["date"] = (datetime.now(ZoneInfo("Asia/Karachi")) + __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d")

    # Fallback: default time
    if not hints["start_time"]:
        hints["start_time"] = "10:00 AM"
        hints["end_time"] = "11:00 AM"

    # Description from body
    hints["description"] = text[:500] if text else ""

    return hints


# ─── Odoo client helper ──────────────────────────────────────────────────

def _get_odoo_client():
    """Try to instantiate OdooClient; return None on failure."""
    try:
        module_file = ROOT / ".agents/skills/odoo-integration/scripts/odoo_client.py"
        spec = importlib.util.spec_from_file_location("odoo_client_dynamic", module_file)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules["odoo_client_dynamic"] = module
        spec.loader.exec_module(module)
        config = module.OdooConfig(
            url=os.getenv("ODOO_URL", "http://localhost:8069"),
            db=os.getenv("ODOO_DB", "odoo_db"),
            user=os.getenv("ODOO_USER", "admin"),
            password=os.getenv("ODOO_PASSWORD", "admin"),
        )
        return module.OdooClient(config)
    except Exception as exc:
        logger.warning("Odoo client unavailable: %s", exc)
        return None


# ─── Execution helpers (Odoo + Email) ────────────────────────────────────

def _save_invoice_to_vault(vault: Path, meta: dict, invoice_id: int | str) -> Path:
    """Save a markdown invoice file to Vault/Invoices/ for Obsidian visibility."""
    invoices_dir = vault / "Invoices"
    invoices_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y%m%d_%H%M%S")
    partner_name = meta.get("partner_name", "Unknown")
    safe_name = re.sub(r'[^\w\-]', '_', partner_name)[:30]
    filepath = invoices_dir / f"INVOICE_{safe_name}_{stamp}.md"
    product = meta.get("product_description", "Product/Service")
    quantity = meta.get("quantity", 1)
    unit_price = meta.get("unit_price", 0.0)
    total = float(quantity) * float(unit_price)
    filepath.write_text(
        f"""---
type: invoice
invoice_id: {invoice_id}
status: draft
date: {datetime.now(ZoneInfo('Asia/Karachi')).strftime('%Y-%m-%d')}
partner_name: {partner_name}
partner_email: {meta.get('partner_email', '')}
subject: {meta.get('subject', '')}
---

# Invoice #{invoice_id}

**Date:** {datetime.now(ZoneInfo('Asia/Karachi')).strftime('%Y-%m-%d')}  
**Customer:** {partner_name}  
**Email:** {meta.get('partner_email', '')}  

## Items

| Product | Qty | Unit Price | Total |
|---------|-----|-----------|-------|
| {product} | {quantity} | {unit_price} | {total:.2f} |

**Total Amount: {total:.2f}**

_Draft invoice created in Odoo (ID: {invoice_id}). Approve in Odoo to finalize._
"""
    )
    return filepath


def execute_invoice_action(meta: dict) -> dict:
    """Create draft invoice in Odoo from approval metadata. Returns result dict."""
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    partner_name = meta.get("partner_name", "Unknown Customer")
    partner_email = meta.get("partner_email", "")
    product = meta.get("product_description", "Product/Service")
    quantity = float(meta.get("quantity", 1))
    unit_price = float(meta.get("unit_price", 0))
    vault = get_vault_path()

    if dry_run:
        msg = (f"[DRY RUN] Would create invoice for {partner_name} — "
               f"{product} x{quantity} @{unit_price}")
        logger.info(msg)
        return {"status": "dry_run", "message": msg}

    client = _get_odoo_client()
    if client is None:
        return {"status": "error", "message": "Odoo not reachable"}

    try:
        partner_result = client.ensure_partner(partner_name, partner_email)
        partner_id = partner_result["partner"]["id"]

        invoice_id = client.create_draft_invoice(
            partner_id=partner_id,
            lines=[{"name": product, "quantity": quantity, "price_unit": unit_price}],
        )
        # Save invoice markdown to Vault/Invoices for Obsidian
        invoice_file = _save_invoice_to_vault(vault, meta, invoice_id)
        return {
            "status": "success",
            "partner_id": partner_id,
            "invoice_id": invoice_id,
            "invoice_file": str(invoice_file.name),
            "message": f"Draft invoice #{invoice_id} created for {partner_name}",
        }
    except Exception as exc:
        logger.error("Odoo invoice creation failed: %s", exc)
        return {"status": "error", "message": str(exc)}


def execute_email_reply(meta: dict, invoice_result: dict) -> dict:
    """Send confirmation email to customer after invoice creation."""
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    to_email = meta.get("partner_email", "")
    original_subject = meta.get("subject", "Your Order")
    invoice_id = invoice_result.get("invoice_id", "N/A")
    partner_name = meta.get("partner_name", "Customer")
    product = meta.get("product_description", "Product/Service")
    quantity = meta.get("quantity", 1)
    unit_price = meta.get("unit_price", 0.0)
    total = float(quantity) * float(unit_price)

    if not to_email:
        return {"status": "skipped", "message": "No partner_email in metadata"}

    subject = f"Re: {original_subject} — Invoice #{invoice_id}"
    body = (
        f"Dear {partner_name},\n\n"
        f"Thank you for your order. We have processed your request.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"           INVOICE #{invoice_id}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Date      : {datetime.now(ZoneInfo('Asia/Karachi')).strftime('%Y-%m-%d')}\n"
        f"Customer  : {partner_name}\n"
        f"\n"
        f"Item      : {product}\n"
        f"Quantity  : {quantity}\n"
        f"Unit Price: {unit_price}\n"
        f"Total     : {total:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Status    : Draft (pending finalization)\n\n"
        f"Our accounts team will finalize and send the official invoice shortly.\n\n"
        f"Best regards,\nAccounts Team"
    )

    if dry_run:
        msg = f"[DRY RUN] Would send confirmation to {to_email}, subject: {subject}"
        logger.info(msg)
        return {"status": "dry_run", "message": msg}

    try:
        module_file = ROOT / ".agents/skills/gmail-send-mcp/scripts/gmail_send_mcp.py"
        spec = importlib.util.spec_from_file_location("gmail_send_dynamic", module_file)
        if spec is None or spec.loader is None:
            return {"status": "error", "message": "Gmail send module not found"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result_msg = module.send_email(to_email, subject, body)
        return {"status": "success", "message": result_msg}
    except Exception as exc:
        logger.error("Email reply failed: %s", exc)
        return {"status": "error", "message": str(exc)}


def execute_calendar_action(meta: dict) -> dict:
    """Create a Google Calendar event from approval metadata."""
    from dateutil import parser as dateutil_parser

    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    title = meta.get("meeting_title", meta.get("subject", "Meeting"))
    meeting_date = meta.get("meeting_date", "")
    start_time = meta.get("meeting_start", "10:00 AM")
    end_time = meta.get("meeting_end", "11:00 AM")
    description = meta.get("meeting_description", "")
    partner_name = meta.get("partner_name", "")
    partner_email = meta.get("partner_email", "")

    # Parse start datetime
    PKT = ZoneInfo("Asia/Karachi")

    try:
        start_dt = dateutil_parser.parse(f"{meeting_date} {start_time}", fuzzy=True)
        # Make timezone-aware in Karachi if naive — ensures "+05:00" in ISO string sent to Google
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=PKT)
    except (ValueError, OverflowError):
        start_dt = datetime.now(PKT).replace(hour=10, minute=0, second=0, microsecond=0)

    # Parse end datetime
    try:
        end_dt = dateutil_parser.parse(f"{meeting_date} {end_time}", fuzzy=True)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=PKT)
    except (ValueError, OverflowError):
        end_dt = start_dt + __import__("datetime").timedelta(hours=1)

    # Ensure end is after start
    if end_dt <= start_dt:
        end_dt = start_dt + __import__("datetime").timedelta(hours=1)

    event_body = {
        "summary": title,
        "description": f"Auto-created from email.\nFrom: {partner_name} <{partner_email}>\n\n{description[:500]}",
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Karachi",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Karachi",
        },
    }

    if dry_run:
        msg = (f"[DRY RUN] Would create calendar event: {title} "
               f"on {meeting_date} {start_time}-{end_time}")
        logger.info(msg)
        return {"status": "dry_run", "message": msg}

    try:
        sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO", "")
        calendar_id = os.getenv("GOOGLE_CALENDAR_ID", os.getenv("CALENDAR_ID", "primary"))

        if sa_json:
            from google.oauth2 import service_account as sa_module
            info = json.loads(sa_json)
            creds = sa_module.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/calendar"],
            )
        else:
            return {"status": "error", "message": "No service account credentials configured"}

        from googleapiclient.discovery import build as gcal_build
        service = gcal_build("calendar", "v3", credentials=creds)
        created = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
        ).execute()

        event_id = created.get("id", "unknown")
        link = created.get("htmlLink", "")
        msg = f"Calendar event created: {title} (ID: {event_id})"
        logger.info(msg)

        # Save meeting file to Vault
        vault = get_vault_path()
        _save_meeting_to_vault(vault, meta, event_id, link, start_dt, end_dt)

        return {"status": "success", "event_id": event_id, "link": link, "message": msg}
    except Exception as exc:
        logger.error("Calendar event creation failed: %s", exc)
        return {"status": "error", "message": str(exc)}


def execute_meeting_email_reply(meta: dict, cal_result: dict) -> dict:
    """Send confirmation email to client after meeting is booked in calendar."""
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    to_email = meta.get("partner_email", "")
    partner_name = meta.get("partner_name", "Customer")
    original_subject = meta.get("subject", "Meeting")
    title = meta.get("meeting_title", original_subject)
    meeting_date = meta.get("meeting_date", "TBD")
    start_time = meta.get("meeting_start", "TBD")
    end_time = meta.get("meeting_end", "TBD")
    event_id = cal_result.get("event_id", "N/A")
    cal_link = cal_result.get("link", "")

    if not to_email:
        return {"status": "skipped", "message": "No partner_email in metadata"}

    subject = f"Re: {original_subject} — Meeting Confirmed"
    body = (
        f"Dear {partner_name},\n\n"
        f"Your meeting has been successfully scheduled. Here are the details:\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"          MEETING CONFIRMATION\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Title     : {title}\n"
        f"Date      : {meeting_date}\n"
        f"Time      : {start_time} - {end_time}\n"
        f"Event ID  : {event_id}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    if cal_link:
        body += f"Calendar Link: {cal_link}\n\n"
    body += (
        f"Please feel free to reach out if you need to reschedule.\n\n"
        f"Best regards,\nAI Employee — Scheduling Team"
    )

    if dry_run:
        msg = f"[DRY RUN] Would send meeting confirmation to {to_email}, subject: {subject}"
        logger.info(msg)
        return {"status": "dry_run", "message": msg}

    try:
        module_file = ROOT / ".agents/skills/gmail-send-mcp/scripts/gmail_send_mcp.py"
        spec = importlib.util.spec_from_file_location("gmail_send_dynamic", module_file)
        if spec is None or spec.loader is None:
            return {"status": "error", "message": "Gmail send module not found"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result_msg = module.send_email(to_email, subject, body)
        return {"status": "success", "message": result_msg}
    except Exception as exc:
        logger.error("Meeting confirmation email failed: %s", exc)
        return {"status": "error", "message": str(exc)}


def _save_meeting_to_vault(vault: Path, meta: dict, event_id: str, link: str,
                           start_dt, end_dt) -> Path:
    """Save a meeting markdown file to Vault/Done/ for Obsidian visibility."""
    done_dir = vault / "Done"
    done_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y%m%d_%H%M%S")
    title = meta.get("meeting_title", meta.get("subject", "Meeting"))
    safe_title = re.sub(r'[^\w\-]', '_', title)[:40]
    filepath = done_dir / f"MEETING_{safe_title}_{stamp}.md"
    filepath.write_text(
        f"""---
type: calendar_event
event_id: {event_id}
title: {title}
date: {start_dt.strftime('%Y-%m-%d')}
start: {start_dt.strftime('%H:%M')}
end: {end_dt.strftime('%H:%M')}
attendee: {meta.get('partner_email', '')}
status: scheduled
---

# {title}

**Date:** {start_dt.strftime('%Y-%m-%d')}
**Time:** {start_dt.strftime('%H:%M')} – {end_dt.strftime('%H:%M')}
**Attendee:** {meta.get('partner_name', '')} ({meta.get('partner_email', '')})
**Calendar Link:** {link}

_Event created automatically from email approval._
"""
    )
    return filepath


def _count_files(folder: Path, pattern: str = "*.md") -> int:
    if not folder.exists():
        return 0
    return sum(1 for _ in folder.rglob(pattern))


def _count_files_flat(folder: Path, pattern: str = "*.md") -> int:
    if not folder.exists():
        return 0
    return sum(1 for _ in folder.glob(pattern))


def _recent_activity_lines(vault: Path, n: int = 20) -> list[str]:
    """Read last n activity lines from existing dashboard."""
    dashboard = vault / "Dashboard.md"
    if not dashboard.exists():
        return []
    content = dashboard.read_text(encoding="utf-8", errors="ignore")
    lines = []
    in_activity = False
    for line in content.splitlines():
        if line.strip().startswith("## Recent Activity"):
            in_activity = True
            continue
        if in_activity:
            if line.startswith("## ") or line.startswith("# "):
                break
            if line.strip():
                lines.append(line)
    return lines[-n:]  # keep only last n


def _collect_invoice_stats(vault: Path) -> dict:
    invoices_dir = vault / "Invoices"
    if not invoices_dir.exists():
        return {"count": 0, "latest": "—"}
    files = sorted(invoices_dir.glob("INVOICE_*.md"), reverse=True)
    if not files:
        return {"count": 0, "latest": "—"}
    # parse latest invoice_id from frontmatter
    latest = files[0]
    inv_id = "—"
    for line in latest.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("invoice_id:"):
            inv_id = line.split(":", 1)[1].strip()
            break
    return {"count": len(files), "latest": f"#{inv_id} ({latest.stem})"}


def _count_rejected_from_logs(vault: Path) -> int:
    """Count total rejected items across all JSON log files."""
    import json as _json
    logs_dir = vault / "Logs"
    if not logs_dir.exists():
        return 0
    total = 0
    for log_file in logs_dir.glob("*.json"):
        if log_file.name.startswith("."):
            continue
        try:
            entries = _json.loads(log_file.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(entries, list):
                total += sum(1 for e in entries if e.get("approval_status") == "rejected")
        except Exception:
            pass
    return total


def refresh_dashboard(vault: Path, activity_line: str | None = None) -> None:
    """Rebuild Dashboard.md with live stats + recent activity log."""
    dashboard = vault / "Dashboard.md"

    # ── Collect existing activity lines before overwriting ──
    existing_lines = _recent_activity_lines(vault, n=50)
    if activity_line:
        stamp = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y-%m-%d %H:%M")
        existing_lines.append(f"- [{stamp}] {activity_line}")
    # Keep last 50
    existing_lines = existing_lines[-50:]

    # ── Live counts ──
    inbox_count     = _count_files_flat(vault / "Inbox")
    needs_count     = _count_files(vault / "Needs_Action")
    pending_count   = _count_files(vault / "Pending_Approval")
    approved_count  = _count_files_flat(vault / "Approved")
    rejected_count  = _count_rejected_from_logs(vault)   # from logs (items moved to Done after rejection)
    done_count      = _count_files_flat(vault / "Done")
    plans_count     = _count_files(vault / "Plans")
    inv_stats       = _collect_invoice_stats(vault)
    meetings_count  = sum(1 for f in (vault / "Done").glob("MEETING_*.md")) if (vault / "Done").exists() else 0
    logs_dir        = vault / "Logs"
    log_days        = len(list(logs_dir.glob("*.json"))) if logs_dir.exists() else 0

    # ── Pending Approval details (names) ──
    pend_dir = vault / "Pending_Approval"
    pend_names = []
    if pend_dir.exists():
        for f in sorted(pend_dir.rglob("*.md"))[:10]:
            pend_names.append(f"  - {f.name}")

    # ── Recent invoices list ──
    inv_dir = vault / "Invoices"
    inv_lines = []
    if inv_dir.exists():
        for f in sorted(inv_dir.glob("INVOICE_*.md"), reverse=True)[:5]:
            inv_lines.append(f"  - {f.name}")

    # ── Recent Done items ──
    done_dir = vault / "Done"
    done_lines = []
    if done_dir.exists():
        for f in sorted(done_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            done_lines.append(f"  - {f.name}")

    now = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y-%m-%d %H:%M:%S")

    pend_block  = "\n".join(pend_names) if pend_names else "  _None_"
    inv_block   = "\n".join(inv_lines)  if inv_lines  else "  _None_"
    done_block  = "\n".join(done_lines) if done_lines  else "  _None_"
    activity_block = "\n".join(existing_lines) if existing_lines else "_No activity yet._"

    # ── Build pending approval wiki-links ──
    pend_dir2 = vault / "Pending_Approval"
    pend_wiki = []
    if pend_dir2.exists():
        for f in sorted(pend_dir2.rglob("*.md"))[:10]:
            stem = f.stem
            pend_wiki.append(f"  - [[Pending_Approval/{f.parent.name}/{stem}|{stem}]]")
    pend_wiki_block = "\n".join(pend_wiki) if pend_wiki else "  _None pending_"

    # ── Build invoice wiki-links ──
    inv_dir2 = vault / "Invoices"
    inv_wiki = []
    if inv_dir2.exists():
        for f in sorted(inv_dir2.glob("INVOICE_*.md"), reverse=True)[:5]:
            inv_wiki.append(f"  - [[Invoices/{f.stem}|{f.stem}]]")
    inv_wiki_block = "\n".join(inv_wiki) if inv_wiki else "  _None_"

    # ── Build done wiki-links with clean display ──
    done_dir2 = vault / "Done"
    done_wiki = []
    if done_dir2.exists():
        for f in sorted(done_dir2.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            done_wiki.append(f"  - [[Done/{f.stem}|{f.stem}]]")
    done_wiki_block = "\n".join(done_wiki) if done_wiki else "  _None_"

    # ── Callout type based on pending count ──
    if pending_count > 5:
        alert_type = "warning"
        alert_icon = "🔴"
    elif pending_count > 0:
        alert_type = "info"
        alert_icon = "🟡"
    else:
        alert_type = "success"
        alert_icon = "🟢"

    content = f"""---
tags: [dashboard, home, status]
updated: {now}
---

# 🤖 AI Employee — Command Center

> [!{alert_type}] System Status — Last synced: `{now}`
> Auto-refreshed by orchestrator every 5 seconds.

---

## 📊 Live Counts

| 📁 Category | # |
|:---|---:|
| 📥 Inbox (new files) | {inbox_count} |
| ⚡ Needs Action | {needs_count} |
| ⏳ Pending Approval | {pending_count} |
| ✅ Approved | {approved_count} |
| ❌ Rejected | {rejected_count} |
| 🏁 Done | {done_count} |
| 📋 Plans Generated | {plans_count} |
| 🧾 Invoices Created | {inv_stats["count"]} |
| 📅 Meetings Scheduled | {meetings_count} |
| 📅 Log Days | {log_days} |

---

## ⏳ Pending Approval ({pending_count}) {alert_icon}

{pend_wiki_block}

> [!tip] To approve, move file to `Vault/Approved/`

---

## 🧾 Recent Invoices ({inv_stats["count"]} total)

**Latest:** `{inv_stats["latest"]}`

{inv_wiki_block}

---

## 🏁 Recently Completed ({done_count} total)

{done_wiki_block}

---

## 🗂️ Quick Navigation

| Section | Link |
|:--------|:-----|
| Business Goals | [[Business_Goals]] |
| Company Handbook | [[Company_Handbook]] |
| Inbox | [[Inbox/]] |
| Plans | [[Plans/]] |
| Pending Approval | [[Pending_Approval/]] |
| Invoices | [[Invoices/]] |
| Schedules | [[Schedules/linkedin_post]] · [[Schedules/facebook_post]] · [[Schedules/twitter_post]] |

---

## 🕐 Recent Activity (last 50 events)

{activity_block}
"""
    dashboard.write_text(content, encoding="utf-8")


# Keep append_dashboard as thin wrapper so all existing call-sites work unchanged
def append_dashboard(vault: Path, message: str) -> None:
    refresh_dashboard(vault, activity_line=message)


def requires_approval(text: str) -> bool:
    sensitive = ["payment", "send", "invoice", "transfer", "bank",
                "meeting", "metting", "schedule", "shudule", "appointment", "calendar", "call"]
    lowered = text.lower()
    return any(word in lowered for word in sensitive)


def create_plan(vault: Path, source_file: Path) -> Path:
    plans = vault / "Plans"
    plans.mkdir(parents=True, exist_ok=True)
    plan_name = f"PLAN_{source_file.stem}_{datetime.now(ZoneInfo('Asia/Karachi')).strftime('%Y%m%d_%H%M%S')}.md"
    plan_path = plans / plan_name
    plan_path.write_text(
        f"""---
created: {datetime.now(ZoneInfo('Asia/Karachi')).isoformat()}
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


def create_approval(vault: Path, source_file: Path, reason: str, content: str = "") -> Path:
    pending = vault / "Pending_Approval"
    pending.mkdir(parents=True, exist_ok=True)
    approval_path = pending / f"APPROVAL_{source_file.stem}_{datetime.now(ZoneInfo('Asia/Karachi')).strftime('%Y%m%d_%H%M%S')}.md"

    # If this is a FILE_ wrapper, try to read the original email from Inbox
    effective_content = content
    if source_file.name.startswith("FILE_"):
        original_name = source_file.name[len("FILE_"):]
        original_path = vault / "Inbox" / original_name
        if original_path.exists():
            try:
                effective_content = original_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

    # Determine if this is an email file with invoice-worthy content
    is_email = source_file.name.startswith(("EMAIL_", "FILE_EMAIL_"))
    low_content = effective_content.lower()
    has_invoice_keyword = any(w in low_content for w in ["invoice", "order", "payment", "bottle", "purchase"])
    has_meeting_keyword = any(w in low_content for w in ["meeting", "metting", "schedule", "shudule", "appointment", "calendar", "call"])

    if is_email and has_invoice_keyword:
        email_meta = parse_email_frontmatter(effective_content)
        hints = extract_invoice_hints(email_meta.get("body", effective_content))
        approval_path.write_text(
            f"""---
type: approval_request
action: create_invoice_and_reply
source: {source_file.name}
partner_name: {email_meta.get('from', 'Unknown Customer')}
partner_email: {email_meta.get('from_email', '')}
subject: {email_meta.get('subject', '')}
product_description: {hints['product_description']}
quantity: {hints['quantity']}
unit_price: {hints['unit_price']}
reason: {reason}
status: pending
---

Move this file to `/Approved` to create a draft invoice in Odoo and send confirmation email.
Move to `/Rejected` to cancel.
"""
        )
    elif is_email and has_meeting_keyword:
        email_meta = parse_email_frontmatter(effective_content)
        hints = extract_meeting_hints(email_meta.get("body", effective_content), email_meta)
        approval_path.write_text(
            f"""---
type: approval_request
action: create_calendar_event
source: {source_file.name}
partner_name: {email_meta.get('from', 'Unknown')}
partner_email: {email_meta.get('from_email', '')}
subject: {email_meta.get('subject', '')}
meeting_title: {hints['title']}
meeting_date: {hints['date']}
meeting_start: {hints['start_time']}
meeting_end: {hints['end_time']}
meeting_description: {hints['description']}
reason: {reason}
status: pending
---

## Meeting Details
- **Title:** {hints['title']}
- **Date:** {hints['date']}
- **Time:** {hints['start_time']} – {hints['end_time']}

Move this file to `/Approved` to create a Google Calendar event.
Move to `/Rejected` to cancel.
"""
        )
    else:
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

    for source_file in needs_action.rglob("*.md"):
        content = source_file.read_text(encoding="utf-8", errors="ignore")

        # For FILE_ wrappers, resolve original email content from Inbox
        effective_content = content
        if source_file.name.startswith("FILE_"):
            original_name = source_file.name[len("FILE_"):]
            original_path = vault / "Inbox" / original_name
            if original_path.exists():
                try:
                    effective_content = original_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

        create_plan(vault, source_file)

        if requires_approval(effective_content):
            approval = create_approval(vault, source_file, "Sensitive action detected", content=effective_content)
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
    done.mkdir(parents=True, exist_ok=True)
    for file in list(approved.rglob("*.md")):
        if not file.exists():
            continue
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
        except FileNotFoundError:
            continue
        meta = parse_email_frontmatter(content)
        action = meta.get("action", "review_and_execute")

        extra_params: dict = {}

        if action == "create_invoice_and_reply":
            # Phase 3: Odoo invoice + email reply
            invoice_result = execute_invoice_action(meta)
            extra_params["invoice"] = invoice_result
            append_dashboard(
                vault,
                f"Invoice action for {file.name}: {invoice_result.get('message', '')}",
            )

            # Send email reply regardless of invoice status (success or dry_run)
            # Only skip on hard errors where partner_email is also missing
            if invoice_result.get("status") != "error" or meta.get("partner_email"):
                email_result = execute_email_reply(meta, invoice_result)
                extra_params["email_reply"] = email_result
                append_dashboard(
                    vault,
                    f"Email reply for {file.name}: {email_result.get('message', '')}",
                )
        elif action == "create_calendar_event":
            # Calendar meeting creation from email
            cal_result = execute_calendar_action(meta)
            extra_params["calendar"] = cal_result
            append_dashboard(
                vault,
                f"Calendar event for {file.name}: {cal_result.get('message', '')}",
            )
            # Send confirmation email to client about the meeting
            if cal_result.get("status") != "error" and meta.get("partner_email"):
                email_result = execute_meeting_email_reply(meta, cal_result)
                extra_params["email_reply"] = email_result
                append_dashboard(
                    vault,
                    f"Meeting confirmation email for {file.name}: {email_result.get('message', '')}",
                )
        else:
            append_dashboard(vault, f"Approved action executed: {file.name}")

        log_action(
            action_type="approved_execution",
            target=file.name,
            parameters=extra_params,
            result="success",
            approval_status="approved",
            approved_by="human",
        )
        dest = done / file.name
        if dest.exists():
            dest = done / f"{file.stem}_{datetime.now(ZoneInfo('Asia/Karachi')).strftime('%H%M%S')}{file.suffix}"
        try:
            shutil.move(str(file), str(dest))
        except FileNotFoundError:
            pass


def process_rejected(vault: Path) -> None:
    rejected = vault / "Rejected"
    done = vault / "Done"
    done.mkdir(parents=True, exist_ok=True)
    for file in rejected.rglob("*.md"):
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
    stamp = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y%m%d_%H%M%S")
    action_path = needs_action / f"SCHEDULED_{meta.get('filename', 'task')}_{stamp}.md"
    action_path.write_text(
        f"""---
type: scheduled_task
task: {meta.get('task', 'custom')}
created: {datetime.now(ZoneInfo('Asia/Karachi')).isoformat()}
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

        # Refresh dashboard with latest counts on every loop
        refresh_dashboard(vault)

        time.sleep(5)


if __name__ == "__main__":
    main()
