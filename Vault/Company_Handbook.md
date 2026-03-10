# 📖 Company Handbook

> [!info] About This Document
> Rules and boundaries for the AI Employee system. All agents must comply with this handbook.

---

## 💬 Communication Rules

- Always be concise and professional.
- Ask for approval before **any** sensitive external action.

---

## 🔒 Permission Boundaries

| Action Category | Auto-Approve Threshold | Always Require Approval |
|:----------------|:----------------------|:------------------------|
| 📧 Email replies | To known contacts | New contacts, bulk sends |
| 💳 Payments | < $50 recurring | All new payees, > $100 |
| 📢 Social media | Draft generation only | Any publish/send action |
| 📁 File operations | Create, read | Delete, move outside vault |

---

## 🥈 Silver Tier Rules

> [!note] Silver Tier
> - LinkedIn posts must be created as drafts in `Vault/Pending_Approval/`.
> - Publishing LinkedIn content is allowed **only** after moving draft to `Vault/Approved/`.
> - Gmail send actions must pass through Human-in-the-Loop approval.
> - Keep `DRY_RUN=true` until end-to-end smoke test passes.

---

## 🥇 Gold Tier Rules

> [!note] Gold Tier
> - Facebook, Instagram, and X posts follow the same **draft → approval** workflow.
> - Odoo actions are **draft-only** — `account.move` and `account.payment` draft records.
> - Never auto-post invoices/payments in Odoo without explicit approval artifacts.
> - Weekly CEO briefing must be generated and reviewed every Monday morning.
> - Use Ralph loop for multi-step automations requiring persistence until completion.

---

## ⚠️ Escalation Protocol

> [!warning] When in Doubt — Escalate
> - If uncertain about any action, create a file in `Vault/Pending_Approval/`.
> - **Never send payments without explicit approval.**
> - Check [[Dashboard]] for current pending items.

---

## 🗂️ Vault Flow

```
Inbox → Needs_Action → Plans → Pending_Approval → Approved → Done
                                       ↓
                                   Rejected
```

See [[Dashboard]] for live system status.
