import subprocess

pid_file = "/tmp/gmail-watcher.pid"

try:
    with open(pid_file, "r", encoding="utf-8") as f:
        pid = f.read().strip()
    subprocess.check_call(["kill", "-0", pid])
    print("✓ gmail-watcher running")
except Exception:
    print("✗ gmail-watcher not running")
    raise SystemExit(1)
