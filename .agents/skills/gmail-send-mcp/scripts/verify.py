import subprocess

pid_file = "/tmp/gmail-send-mcp.pid"

try:
    with open(pid_file, "r", encoding="utf-8") as f:
        pid = f.read().strip()
    subprocess.check_call(["kill", "-0", pid])
    print("✓ gmail-send-mcp running")
except Exception:
    print("✗ gmail-send-mcp not running")
    raise SystemExit(1)
