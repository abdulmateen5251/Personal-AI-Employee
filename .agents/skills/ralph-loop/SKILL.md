```skill
---
name: ralph-loop
description: Persistence loop utility that keeps re-running task commands until completion conditions are met.
---
```

# Ralph Loop

Implements a persistence pattern for long multi-step tasks by repeatedly running a command until completion criteria are satisfied.

## Usage
```bash
python3 scripts/ralph_loop.py \
  --command "python3 .agents/skills/orchestrator/scripts/orchestrator.py" \
  --done-file "Vault/Done/TASK_COMPLETE.md" \
  --max-iterations 10
```

## Completion Conditions
- Done file exists, or
- Completion token appears in command stdout (`--completion-token`).
