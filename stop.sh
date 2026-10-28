#!/usr/bin/env bash
# Stop only the noVNC/Isaac sessions this launcher recorded and can still verify.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DISPLAY_NUM="${DISPLAY_NUM:-:1}"
LOG_DIR="${LOG_DIR:-/workspace/novnc-logs}"
mkdir -p "$LOG_DIR"
exec 9>"$LOG_DIR/.stack.lock"
flock -w 30 9 || { echo "[stop] Another noVNC start/stop is still running." >&2; exit 1; }
python3 "$SCRIPT_DIR/process_control.py" --log-dir "$LOG_DIR" --display "$DISPLAY_NUM" stop
echo "[stop] Verified desktop/GUI sessions stopped; stale or unverified PIDs were left alone."
echo "[stop] The pod remains running. Restart with: bash novnc.sh"
