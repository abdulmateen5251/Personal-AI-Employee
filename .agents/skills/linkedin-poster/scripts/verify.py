import subprocess

pid_file = "/tmp/linkedin-poster.pid"

try:
    with open(pid_file, "r", encoding="utf-8") as f:
        pid = f.read().strip()
    subprocess.check_call(["kill", "-0", pid])
    print("✓ linkedin-poster running")
except Exception:
    print("✗ linkedin-poster not running")
    raise SystemExit(1)
