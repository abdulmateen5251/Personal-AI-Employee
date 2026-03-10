# Qwen CLI Gmail Reply Flow (Full Structure)

## Objective
Jab meri Gmail par nayi email aaye, to us ka smart draft/reply Qwen CLI generate kare, human approval ke baad send ho.

---

## 1. Required Running Services

1. `gmail-watcher`  
2. `filesystem-watcher`  
3. `qwen-agent`  
4. `orchestrator` (optional for non-Qwen flows, dashboard updates)

Reference files:
- `.agents/skills/gmail-watcher/scripts/gmail_watcher.py`
- `.agents/skills/filesystem-watcher/scripts/filesystem_watcher.py`
- `.agents/skills/qwen-agent/scripts/qwen_agent.py`

---

## 2. End-to-End Pipeline

1. New email arrives in Gmail inbox.
2. Gmail watcher writes markdown file:
   - `Vault/Inbox/EMAIL_<id>.md`
3. Filesystem watcher copies/creates action file:
   - `Vault/Needs_Action/FILE_EMAIL_<id>.md` (or related md flow)
4. Qwen agent picks unprocessed file from `Vault/Needs_Action/`.
5. Qwen agent builds prompt with:
   - `Vault/Company_Handbook.md`
   - `Vault/Business_Goals.md`
   - Source item content
6. Qwen agent calls Qwen CLI (`_call_qwen`):
   - `qwen --yolo --max-session-turns 30 --output-format text "<prompt>"`
7. Qwen output se draft save hota hai:
   - `Vault/Pending_Approval/email/DRAFT_<source>_<timestamp>.md`
8. Human review:
   - Approve: move file to `Vault/Approved/`
   - Reject: move file to `Vault/Rejected/`
9. On approve, action execute:
   - `send_email(...)` via `gmail-send-mcp`
10. File moves to:
   - `Vault/Done/`
11. Audit + dashboard update:
   - `Vault/Logs/YYYY-MM-DD.json`
   - `Vault/Dashboard.md`

---

## 3. Qwen Request Structure (Prompt Contract)

Qwen agent prompt includes:

- Role:
  - "You are the Personal AI Employee..."
- Context:
  - Company handbook + business goals
- Input item:
  - filename, type, full/trimmed content
- Required output artifacts:
  1. Plan file in `Vault/Plans/`
  2. Draft file in `Vault/Pending_Approval/<type>/`

Mandatory draft frontmatter:

```yaml
---
type: email
action: send_email
source: <original_file>
to: <recipient_email>
subject: <reply_subject>
status: pending_approval
created: <iso_timestamp>
---


Approval File Example (Email Reply)


---
type: email
action: send_email
source: EMAIL_ABC123.md
to: client@example.com
subject: Re: Pricing Inquiry
status: pending_approval
created: 2026-03-10T10:30:00Z
---

## Summary
Client ko pricing details ka concise reply bhejna.

## Proposed Action
Dear Client,

Thank you for your email...
[full reply body]

Best regards,
Accounts Team

## Reasoning
Known contact, business context matched, handbook policy followed.

---
Move to Vault/Approved/ to execute or Vault/Rejected/ to cancel.