import subprocess

pid_file = "/tmp/calendar-watcher.pid"

try:
    with open(pid_file, "r", encoding="utf-8") as f:
        pid = f.read().strip()
    subprocess.check_call(["kill", "-0", pid])
    print("✓ calendar-watcher running")
except Exception:
    print("✗ calendar-watcher not running")
    raise SystemExit(1)
