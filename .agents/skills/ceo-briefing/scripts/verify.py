import subprocess

pid_file = "/tmp/ceo-briefing.pid"

try:
    with open(pid_file, "r", encoding="utf-8") as f:
        pid = f.read().strip()
    subprocess.check_call(["kill", "-0", pid])
    print("✓ ceo-briefing running")
except Exception:
    print("✗ ceo-briefing not running")
    raise SystemExit(1)
