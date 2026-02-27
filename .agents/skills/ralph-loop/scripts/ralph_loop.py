from __future__ import annotations

import argparse
from datetime import datetime
import json
import shlex
import subprocess
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import get_vault_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ralph-style persistence loop")
    parser.add_argument("--command", required=True, help="Command to execute each iteration")
    parser.add_argument("--done-file", required=False, default="", help="Completion file path (absolute or workspace-relative)")
    parser.add_argument("--completion-token", required=False, default="", help="Token that marks completion in stdout")
    parser.add_argument("--max-iterations", type=int, default=10)
    parser.add_argument("--sleep-seconds", type=int, default=5)
    return parser.parse_args()


def _resolve_done_file(done_file: str) -> Path | None:
    if not done_file:
        return None
    p = Path(done_file)
    if p.is_absolute():
        return p
    return ROOT / p


def _state_path(vault: Path) -> Path:
    p = vault / "Logs" / ".ralph-loop-state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def main() -> None:
    args = parse_args()
    vault = get_vault_path()
    done_path = _resolve_done_file(args.done_file)

    state = {
        "started_at": datetime.utcnow().isoformat() + "Z",
        "command": args.command,
        "max_iterations": args.max_iterations,
        "iterations": [],
    }

    for i in range(1, args.max_iterations + 1):
        proc = subprocess.run(
            shlex.split(args.command),
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        iteration = {
            "iteration": i,
            "returncode": proc.returncode,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stdout_tail": out[-2000:],
        }
        state["iterations"].append(iteration)
        _state_path(vault).write_text(json.dumps(state, indent=2))

        file_complete = bool(done_path and done_path.exists())
        token_complete = bool(args.completion_token and args.completion_token in out)

        if file_complete or token_complete:
            state["completed"] = True
            state["completed_at"] = datetime.utcnow().isoformat() + "Z"
            state["completion_reason"] = "done_file" if file_complete else "completion_token"
            _state_path(vault).write_text(json.dumps(state, indent=2))
            print("Ralph loop complete")
            return

        time.sleep(args.sleep_seconds)

    state["completed"] = False
    state["completed_at"] = datetime.utcnow().isoformat() + "Z"
    state["completion_reason"] = "max_iterations_reached"
    _state_path(vault).write_text(json.dumps(state, indent=2))
    print("Ralph loop reached max iterations without completion")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
