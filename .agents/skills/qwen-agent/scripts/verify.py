"""Verify Qwen Code agent setup."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

checks = []

# 1. Qwen Code CLI
qwen_bin = shutil.which("qwen")
if qwen_bin:
    checks.append(("qwen CLI", True, qwen_bin))
else:
    checks.append(("qwen CLI", False, "not found — install: npm install -g @qwen-ai/qwen-code"))

# 2. QWEN.md system prompt
qwen_md = ROOT / "QWEN.md"
checks.append(("QWEN.md", qwen_md.exists(), str(qwen_md.relative_to(ROOT))))

# 3. .qwen/settings.json (hooks)
settings = ROOT / ".qwen" / "settings.json"
checks.append((".qwen/settings.json", settings.exists(), str(settings.relative_to(ROOT))))

# 4. Ralph stop hook
hook = ROOT / ".qwen" / "hooks" / "ralph_stop_hook.py"
checks.append(("ralph_stop_hook.py", hook.exists(), str(hook.relative_to(ROOT))))

# 5. Vault/Needs_Action
needs_action = ROOT / "Vault" / "Needs_Action"
checks.append(("Vault/Needs_Action", needs_action.exists(), str(needs_action.relative_to(ROOT))))

# 6. qwen_agent.py
agent_script = ROOT / ".agents" / "skills" / "qwen-agent" / "scripts" / "qwen_agent.py"
checks.append(("qwen_agent.py", agent_script.exists(), str(agent_script.relative_to(ROOT))))

print("\n=== Qwen Agent Verification ===\n")
all_ok = True
for name, ok, detail in checks:
    status = "✅" if ok else "❌"
    print(f"  {status}  {name}: {detail}")
    if not ok:
        all_ok = False

print()
if all_ok:
    print("All checks passed. Run: bash .agents/skills/qwen-agent/scripts/start.sh")
else:
    print("Some checks failed. Fix the issues above before starting.")
    sys.exit(1)
