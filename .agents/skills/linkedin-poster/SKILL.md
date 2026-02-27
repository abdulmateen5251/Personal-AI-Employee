```skill
---
name: linkedin-poster
description: Automatically generates and posts LinkedIn content from business goals. Includes OAuth2 setup, draft approval workflow, and scheduled posting.
---
```

# LinkedIn Poster

Generates LinkedIn posts based on your business goals and active projects, routes them through the Human-in-the-Loop approval workflow, then publishes approved posts via the LinkedIn Posts API.

## Tools / Capabilities

| Capability | Description |
|------------|-------------|
| Content generation | Reads `Business_Goals.md` and `Active_Project/` to draft posts |
| HITL approval | Drafts go to `/Pending_Approval` before posting |
| Scheduled posting | Works with orchestrator scheduler for regular posting |
| Post tracking | Logs all posts to audit trail |

## Server Lifecycle

### Start
```bash
bash scripts/start.sh
```

### Stop
```bash
bash scripts/stop.sh
```

### Verify
```bash
python3 scripts/verify.py
```

## Configuration

| Variable | Description |
|----------|-------------|
| `LINKEDIN_CLIENT_ID` | LinkedIn app client ID |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn app client secret |
| `LINKEDIN_TOKEN_PATH` | Path to saved OAuth token JSON |
| `LINKEDIN_PERSON_URN` | Your LinkedIn person URN (e.g., `urn:li:person:ABC123`) |

## Setup

1. Create a LinkedIn Developer App at https://www.linkedin.com/developers/apps
2. Request `w_member_social` scope (Share on LinkedIn product)
3. Add `http://localhost:8585/callback` as a redirect URI
4. Set environment variables in `.env`
5. Run OAuth flow: `python3 scripts/linkedin_oauth_setup.py`

## Behavior

1. **Draft generation**: Reads vault context, generates a post draft as `LINKEDIN_DRAFT_*.md` in `/Pending_Approval`
2. **Approval**: User moves file to `/Approved` to permit posting
3. **Posting**: Poster detects approved drafts, calls LinkedIn API, moves to `/Done`
4. **Logging**: Every post (or dry-run) is audit-logged

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Token expired | LinkedIn tokens last 60 days; re-run `linkedin_oauth_setup.py` |
| 403 on post | Ensure your app has the "Share on LinkedIn" product enabled |
| No drafts generated | Check that `Business_Goals.md` exists and has content |
