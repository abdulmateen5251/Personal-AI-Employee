#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
PID_FILE="/tmp/gmail-send-mcp.pid"
FIFO_FILE="/tmp/gmail-send-mcp-stdin.fifo"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "gmail-send-mcp already running"
  exit 0
fi

# Create a named FIFO so MCP server stdin never receives EOF
# (stdio transport exits immediately when stdin is /dev/null under nohup)
rm -f "$FIFO_FILE"
mkfifo "$FIFO_FILE"

cd "$ROOT_DIR"

# Start MCP server reading from FIFO
nohup "$PYTHON_BIN" .agents/skills/gmail-send-mcp/scripts/gmail_send_mcp.py \
  <"$FIFO_FILE" >>/tmp/gmail-send-mcp.log 2>&1 &
MCP_PID=$!
echo $MCP_PID > "$PID_FILE"

# Keep the FIFO write-end permanently open so MCP stdin stays alive
nohup bash -c "exec 3>\"$FIFO_FILE\"; sleep infinity" >/dev/null 2>&1 &

echo "gmail-send-mcp started (pid $MCP_PID)"
