import json
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import get_vault_path


def _log_path() -> Path:
    vault = get_vault_path()
    logs_dir = vault / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    filename = datetime.now(timezone.utc).strftime("%Y-%m-%d.json")
    return logs_dir / filename


def log_action(
    action_type: str,
    target: str,
    parameters: dict,
    result: str,
    approval_status: str = "n/a",
    approved_by: str = "n/a",
    actor: str = "qwen_code",
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "actor": actor,
        "target": target,
        "parameters": parameters,
        "approval_status": approval_status,
        "approved_by": approved_by,
        "result": result,
    }
    path = _log_path()
    if path.exists():
        content = json.loads(path.read_text())
    else:
        content = []
    content.append(entry)
    path.write_text(json.dumps(content, indent=2))
