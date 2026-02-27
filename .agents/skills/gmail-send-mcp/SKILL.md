```skill
---
name: gmail-send-mcp
description: MCP server that sends and drafts emails via the Gmail API.
---
```

# Gmail Send MCP Server

An MCP (Model Context Protocol) server exposing Gmail send and draft capabilities as tools. Uses the `FastMCP` SDK over STDIO transport.

## Tools Provided

| Tool | Description |
|------|-------------|
| `send_email` | Send an email to a recipient (respects DRY_RUN) |
| `draft_email` | Create a draft email in Gmail |
| `list_drafts` | List recent drafts |

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

Requires these environment variables in `.env`:

| Variable | Description |
|----------|-------------|
| `GMAIL_TOKEN_PATH` | Path to Gmail OAuth token (with `gmail.send` scope) |
| `DRY_RUN` | When `true`, logs instead of sending |

## Behavior

- In `DRY_RUN` mode, `send_email` logs the intent but does not send.
- All actions are audit-logged to `Vault/Logs/`.
- Integrates with the orchestrator's HITL approval workflow — sensitive sends route through `/Pending_Approval`.

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Token missing | Run `gmail_oauth_setup.py` with `gmail.send` scope |
| Permission denied | Ensure OAuth token has `gmail.send` and `gmail.modify` scopes |
| MCP connection fails | Check STDIO transport; ensure server process is running |
