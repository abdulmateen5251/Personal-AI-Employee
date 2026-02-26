import subprocess

pid_file = "/tmp/finance-watcher.pid"

try:
    with open(pid_file, "r", encoding="utf-8") as f:
        pid = f.read().strip()
    subprocess.check_call(["kill", "-0", pid])
    print("✓ finance-watcher running")
except Exception:
    print("✗ finance-watcher not running")
    raise SystemExit(1)
