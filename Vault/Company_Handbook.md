# Company Handbook

## Communication Rules
- Always be concise and professional.
- Ask for approval before sensitive external actions.

## Permission Boundaries
| Action Category | Auto-Approve Threshold | Always Require Approval |
| :---- | :---- | :---- |
| Email replies | To known contacts | New contacts, bulk sends |
| Payments | < $50 recurring | All new payees, > $100 |
| Social media | Draft generation only | Any publish/send action |
| File operations | Create, read | Delete, move outside vault |

## Silver Tier Rules
- LinkedIn posts must be created as draft files in `/Pending_Approval`.
- Publishing LinkedIn content is allowed only after moving draft files to `/Approved`.
- Gmail send actions must pass through Human-in-the-Loop approval.
- Keep `DRY_RUN=true` until end-to-end smoke test passes.

## Gold Tier Rules
- Facebook, Instagram, and X posts must follow the same draft → approval workflow.
- Odoo actions are draft-only (`account.move` and `account.payment` draft records).
- Never auto-post invoices/payments in Odoo without explicit approval artifacts.
- Weekly CEO briefing must be generated and reviewed every Monday morning.
- Use Ralph loop for multi-step automations that require persistence until completion.

## Escalation
- If uncertain, create a file in `/Pending_Approval`.
- Never send payments without explicit approval.
