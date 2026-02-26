import subprocess

pid_file = "/tmp/orchestrator.pid"

try:
    with open(pid_file, "r", encoding="utf-8") as f:
        pid = f.read().strip()
    subprocess.check_call(["kill", "-0", pid])
    print("✓ orchestrator running")
except Exception:
    print("✗ orchestrator not running")
    raise SystemExit(1)
