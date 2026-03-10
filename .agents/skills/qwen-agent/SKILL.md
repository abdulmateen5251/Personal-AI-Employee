```skill
---
name: qwen-agent
description: Autonomous Qwen Code agent loop — reads Needs_Action, reasons via Qwen Code CLI, writes drafts to Pending_Approval, and executes approved MCP actions.
---
```

# Qwen Agent

The core reasoning brain of the Personal AI Employee. This skill integrates
Qwen Code CLI as the autonomous reasoning engine over the Obsidian Vault.

## Architecture

```
Filesystem Watcher / Gmail Watcher
        ↓ (writes files)
  Vault/Needs_Action/
        ↓ (reads + prompts qwen CLI)
    qwen_agent.py
        ↓ (writes drafts)
  Vault/Pending_Approval/
        ↓ (human approves → moves to Approved/)
    qwen_agent.py (detects Approved/)
        ↓ (calls MCP)
  Gmail Send MCP / Social Poster / Odoo MCP
        ↓
  Vault/Done/
```

## Ralph Wiggum Stop Hook

The `.qwen/hooks/ralph_stop_hook.py` runs after every Qwen Code response.
It checks if `Vault/Needs_Action/` has remaining items:
- If YES → injects a "continue" message (exit code 2) → Qwen keeps working
- If NO → exits 0 → Qwen stops

## Usage

Start (polling loop):
```bash
bash .agents/skills/qwen-agent/scripts/start.sh
```

Run once (for testing):
```bash
.venv/bin/python .agents/skills/qwen-agent/scripts/qwen_agent.py --once
```

Stop:
```bash
bash .agents/skills/qwen-agent/scripts/stop.sh
```

Verify:
```bash
.venv/bin/python .agents/skills/qwen-agent/scripts/verify.py
```

## Manual Qwen Code (Interactive Mode)

To run Qwen Code interactively with the full system prompt:
```bash
cd /home/abdul-matten/Desktop/Personal-AI-Employee
qwen
```

Qwen Code will automatically read `QWEN.md` as its system instructions and
`.qwen/settings.json` for the Ralph Wiggum Stop Hook.
