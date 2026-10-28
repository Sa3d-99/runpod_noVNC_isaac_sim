#!/usr/bin/env bash
# =============================================================================
# novnc.sh — PRIMARY METHOD: view Isaac Sim's full GUI in a browser on RunPod.
#
# Works on ALL Isaac Sim versions (4.0, 4.1, 4.2, 4.5, 5.x) because it does not
# touch Isaac's streaming stack at all — it renders Isaac into a virtual X
# display and ships that display to the browser over plain HTTP + WebSocket,
# which is exactly what RunPod's proxy already carries.
#
#   Xvfb (virtual screen)  <- Isaac Sim GUI renders here (GPU / Vulkan)
#        ^-- x11vnc          exposes that screen as VNC on :5900 (localhost)
#              ^-- websockify+noVNC  serve it as a web page on :$WEB_PORT
#                    ^-- browser: https://<POD>-<WEB_PORT>.proxy.runpod.net/vnc.html
#
# No UDP. No WebRTC. No ICE. No TURN. No Direct-TCP ports. Nothing to expose
# beyond the HTTP port RunPod already gives you.
#
# USAGE (inside the container; SSH is more stable than the web terminal):
#   bash novnc.sh
# Then open the URL it prints. Load your scene with File > Open in the GUI.
#
# Env overrides:
#   WEB_PORT=8080        HTTP port noVNC is served on (must be exposed as HTTP)
#   RES=1920x1080        virtual screen resolution
#   ISAAC_ROOT=/isaac-sim
#   VNC_PASSWORD=...     set a VNC password (default: none, pod is private)
#   NO_ISAAC=1           only bring up the desktop, don't launch Isaac
#   LOG_DIR=/workspace/novnc-logs
# =============================================================================
set -euo pipefail

WEB_PORT="${WEB_PORT:-8080}"
RES="${RES:-1920x1080}"
ISAAC_ROOT="${ISAAC_ROOT:-/isaac-sim}"
DISPLAY_NUM="${DISPLAY_NUM:-:1}"
LOG_DIR="${LOG_DIR:-/workspace/novnc-logs}"
VNC_PORT="${VNC_PORT:-5900}"
mkdir -p "$LOG_DIR"

log() { echo "[novnc] $*"; }
die() { echo "[novnc] ERROR: $*" >&2; exit 1; }

# Is a TCP port accepting connections on localhost? Pure bash — deliberately does
# NOT use `ss`/`netstat`, which are not installed on the Isaac images.
port_open() {
    (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && { exec 3<&-; exec 3>&-; return 0; }
    return 1
}

# Wait up to N seconds for a port to come up.
wait_port() {
    local port="$1" secs="${2:-15}"
    for _ in $(seq 1 "$secs"); do
        port_open "$port" && return 0
        sleep 1
    done
    return 1
}

# --- 1. dependencies (git, python3, Xvfb, x11vnc, fluxbox, noVNC, websockify) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "$SCRIPT_DIR/install.sh" && -f "$SCRIPT_DIR/process_control.py" ]] \
    || die "Use bootstrap.sh to download the full repository, including process_control.py."
bash "$SCRIPT_DIR/install.sh"

# --- 2. stop only sessions recorded by this launcher -----------------------------
CONTROL="$SCRIPT_DIR/process_control.py"
[[ -f "$CONTROL" ]] || die "Missing process_control.py; use bootstrap.sh to download the full repository."
exec 9>"$LOG_DIR/.stack.lock"
flock -n 9 || die "Another noVNC start/stop is in progress. Wait for it to finish."
managed() { python3 "$CONTROL" --log-dir "$LOG_DIR" --display "$DISPLAY_NUM" "$@"; }
managed_start() {
    local name="$1"
    if ! managed start "$@"; then
        [[ ! -f "$LOG_DIR/$name.log" ]] || tail -n 40 "$LOG_DIR/$name.log" >&2
        die "Could not start $name; see $LOG_DIR/$name.log"
    fi
}
log "Cleaning up verified sessions from our previous noVNC stack..."
managed stop
# Never unlink another display's sockets or kill processes by a name pattern.
if xdpyinfo -display "$DISPLAY_NUM" >/dev/null 2>&1; then
    die "Display $DISPLAY_NUM is already in use by an unverified server. Choose another DISPLAY_NUM."
fi
port_open "$VNC_PORT" && die "VNC port $VNC_PORT is already in use."
port_open "$WEB_PORT" && die "HTTP port $WEB_PORT is already in use."

export DISPLAY="$DISPLAY_NUM"

# --- 3. virtual display + window manager ---------------------------------------
log "Starting virtual display ${DISPLAY_NUM} at ${RES}..."
managed_start xvfb -- Xvfb "$DISPLAY_NUM" -screen 0 "${RES}x24" +extension GLX +render -noreset
for _ in $(seq 1 15); do
    xdpyinfo -display "$DISPLAY_NUM" >/dev/null 2>&1 && break
    sleep 1
done
xdpyinfo -display "$DISPLAY_NUM" >/dev/null 2>&1 \
    || die "Xvfb failed to start — see $LOG_DIR/xvfb.log"
log "Virtual display up."

managed_start fluxbox -- fluxbox
sleep 1

# --- 4. VNC server on that display ----------------------------------------------
if [[ -n "${VNC_PASSWORD:-}" ]]; then
    x11vnc -storepasswd "$VNC_PASSWORD" "$LOG_DIR/vncpass" >/dev/null 2>&1
    AUTH=(-rfbauth "$LOG_DIR/vncpass")
    log "VNC password enabled."
else
    AUTH=(-nopw)
fi
log "Starting VNC server on localhost:${VNC_PORT}..."
managed_start x11vnc -- x11vnc -display "$DISPLAY_NUM" -forever -shared "${AUTH[@]}" \
    -rfbport "$VNC_PORT" -localhost -noxdamage
sleep 2
wait_port "$VNC_PORT" 15 \
    || die "x11vnc failed to bind :${VNC_PORT} — see $LOG_DIR/x11vnc.log"
log "VNC server up."

# --- 5. noVNC web front-end (HTTP + WebSocket, rides RunPod's HTTP proxy) -------
log "Starting noVNC web server on :${WEB_PORT}..."
managed_start websockify -- websockify --web=/usr/share/novnc "$WEB_PORT" "localhost:${VNC_PORT}"
sleep 2
wait_port "$WEB_PORT" 15 \
    || die "websockify failed to bind :${WEB_PORT} — see $LOG_DIR/websockify.log"
log "noVNC web server up."

# --- 6. launch the Isaac Sim GUI on the virtual display -------------------------
# Launcher name differs across versions, so probe for whichever exists:
#   4.x            -> isaac-sim.sh / runapp.sh
#   5.x / variants -> isaac-sim.selector.sh, or kit with the GUI .kit app
GUI_STARTED=0
if [[ "${NO_ISAAC:-0}" == "1" ]]; then
    log "NO_ISAAC=1 — desktop only, skipping Isaac launch."
else
    cd "$ISAAC_ROOT"
    GUI_LAUNCHER=""
    for cand in ./isaac-sim.sh ./runapp.sh ./isaac-sim.selector.sh; do
        [[ -x "$cand" ]] && { GUI_LAUNCHER="$cand"; break; }
    done
    if [[ -z "$GUI_LAUNCHER" ]]; then
        # last resort: run the GUI .kit app directly through kit
        GUI_KIT="$(ls apps/*isaac.sim.kit apps/isaacsim.exp.full.kit 2>/dev/null | head -1 || true)"
        if [[ -n "$GUI_KIT" && -x ./kit/kit ]]; then
            log "Launching Isaac Sim GUI via kit + ${GUI_KIT}..."
            managed_start isaac-gui -- ./kit/kit "$GUI_KIT" \
                --ext-folder ./apps --allow-root
            GUI_STARTED=1
        else
            log "WARNING: no Isaac GUI launcher found under $ISAAC_ROOT."
            log "Desktop is up — start Isaac yourself with: DISPLAY=$DISPLAY_NUM <launcher>"
        fi
    else
        log "Launching Isaac Sim GUI (${GUI_LAUNCHER}) on ${DISPLAY_NUM}..."
        managed_start isaac-gui -- "$GUI_LAUNCHER" --allow-root
        GUI_STARTED=1
    fi
fi

if [[ "$GUI_STARTED" == 1 ]]; then
    sleep 2
    if ! managed status isaac-gui; then
        log "WARNING: Isaac GUI exited during startup; the browser desktop is still available."
        tail -n 40 "$LOG_DIR/isaac-gui.log" || true
        GUI_STARTED=0
    fi
fi

# --- 7. print the REAL URL --------------------------------------------------------
# Never print a <POD_ID> placeholder — either we can build the real link or we say
# exactly how to get it. RunPod injects RUNPOD_POD_ID; fall back to parsing the
# pod id out of the SSH/hostname info if that env var is missing.
POD="${RUNPOD_POD_ID:-}"
if [[ -z "$POD" ]]; then
    # RunPod sets RUNPOD_POD_HOSTNAME like "<podid>-<suffix>"
    POD="${RUNPOD_POD_HOSTNAME:-}"
    POD="${POD%%-*}"
fi

echo ""
echo "=================================================================="
if [[ -n "$POD" ]]; then
    URL="https://${POD}-${WEB_PORT}.proxy.runpod.net/vnc.html?autoconnect=1&resize=remote"
    echo "$URL" > "$LOG_DIR/novnc_url.txt"
    echo "  noVNC desktop is UP. Open this in your browser:"
    echo ""
    echo "    $URL"
    echo ""
    echo "  (also saved to $LOG_DIR/novnc_url.txt)"
else
    echo "  noVNC desktop is UP on port ${WEB_PORT}, but the pod id is not in the"
    echo "  environment, so the exact URL can't be built here."
    echo ""
    echo "  Get it from the RunPod console: your Pod -> Connect ->"
    echo "  the HTTP Service link for port ${WEB_PORT}, then append:"
    echo "      /vnc.html?autoconnect=1&resize=remote"
    echo ""
    echo "  It looks like:"
    echo "      https://<POD_ID>-${WEB_PORT}.proxy.runpod.net/vnc.html?autoconnect=1&resize=remote"
fi
echo ""
if [[ "$GUI_STARTED" == 1 ]]; then
    echo "  Isaac Sim GUI takes 1-2 min to appear on the desktop."
    echo "  Then load your scene with  File > Open  inside the GUI."
else
    echo "  Desktop is up. Isaac GUI was skipped, unavailable, or exited; check isaac-gui.log."
fi
echo "=================================================================="
echo ""
log "Everything runs in a detached session — survives terminal/SSH disconnect."
log "Logs: $LOG_DIR/{xvfb,x11vnc,websockify,fluxbox,isaac-gui}.log"
