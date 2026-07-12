#!/usr/bin/env bash
# =============================================================================
# novnc.sh — view Isaac Sim's full GUI in a browser on RunPod via noVNC.
#
# WHY THIS instead of WebRTC:
#   Isaac Sim's built-in WebRTC/native streaming needs UDP + reachable IPs, which
#   RunPod's TCP-proxy-only network cannot provide. noVNC sidesteps all of it:
#   Isaac renders into a virtual X display, a VNC server exposes that display,
#   and noVNC serves it to the browser over plain HTTP + WebSocket — exactly what
#   RunPod's HTTP proxy already carries. Full mouse/keyboard, load your own scene.
#
# HOW IT WORKS:
#   Xvfb (virtual screen) <- Isaac Sim GUI renders here (GPU via Vulkan)
#        ^-- x11vnc exposes it as VNC on :5900
#              ^-- websockify+noVNC serve it as a web page on :$WEB_PORT
#                    ^-- browser opens https://<POD>-<WEB_PORT>.proxy.runpod.net/vnc.html
#
# ONE-TIME RUNPOD SETUP:
#   Expose 8080 as an HTTP port (already default on most Isaac images). We serve
#   noVNC on 8080 so it rides the HTTP proxy — no Direct TCP port needed.
#
# USAGE (inside the container, SSH recommended over the flaky web terminal):
#   bash novnc.sh
# Then open the URL it prints. Password is disabled (private pod); add one via
#   VNC_PASSWORD=yourpass bash novnc.sh   if you want.
#
# Env overrides: WEB_PORT (8080), RES (1920x1080), ISAAC_ROOT (/isaac-sim),
#                DISPLAY_NUM (:1), LOG_DIR (/workspace/novnc-logs)
# =============================================================================
set -euo pipefail

WEB_PORT="${WEB_PORT:-8080}"
RES="${RES:-1920x1080}"
ISAAC_ROOT="${ISAAC_ROOT:-/isaac-sim}"
DISPLAY_NUM="${DISPLAY_NUM:-:1}"
LOG_DIR="${LOG_DIR:-/workspace/novnc-logs}"
VNC_PORT=5900
mkdir -p "$LOG_DIR"

log() { echo "[novnc] $*"; }

# --- 1. install dependencies --------------------------------------------------
NEED=()
for c in Xvfb x11vnc fluxbox websockify; do command -v "$c" >/dev/null 2>&1 || NEED+=("$c"); done
[[ -d /usr/share/novnc ]] || NEED+=(novnc)
if [[ ${#NEED[@]} -gt 0 ]]; then
    log "Installing: ${NEED[*]} ..."
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        xvfb x11vnc fluxbox novnc websockify x11-utils >/dev/null
fi

# --- 2. clean any previous run of THIS stack (never touches Isaac headless) ----
pkill -f "Xvfb $DISPLAY_NUM" 2>/dev/null || true
pkill -f "x11vnc.*$VNC_PORT" 2>/dev/null || true
pkill -f "websockify.*$WEB_PORT" 2>/dev/null || true
pkill -f 'isaac-sim.sh' 2>/dev/null || true
pkill -f 'omni.isaac.sim.kit' 2>/dev/null || true   # the GUI kit app (not headless)
sleep 2

export DISPLAY="$DISPLAY_NUM"

# --- 3. virtual display + window manager --------------------------------------
log "Starting virtual display $DISPLAY_NUM at $RES ..."
setsid Xvfb "$DISPLAY_NUM" -screen 0 "${RES}x24" +extension GLX +render -noreset \
    </dev/null >"$LOG_DIR/xvfb.log" 2>&1 &
sleep 3
# confirm the display is up
if ! DISPLAY="$DISPLAY_NUM" xdpyinfo >/dev/null 2>&1; then
    log "ERROR: Xvfb did not start — see $LOG_DIR/xvfb.log"
    exit 1
fi
setsid fluxbox </dev/null >"$LOG_DIR/fluxbox.log" 2>&1 &
sleep 1

# --- 4. VNC server on the virtual display -------------------------------------
log "Starting x11vnc on port $VNC_PORT ..."
if [[ -n "${VNC_PASSWORD:-}" ]]; then
    x11vnc -storepasswd "$VNC_PASSWORD" "$LOG_DIR/vncpass" >/dev/null 2>&1
    AUTH=(-rfbauth "$LOG_DIR/vncpass")
else
    AUTH=(-nopw)
fi
setsid x11vnc -display "$DISPLAY_NUM" -forever -shared "${AUTH[@]}" \
    -rfbport "$VNC_PORT" -noxdamage </dev/null >"$LOG_DIR/x11vnc.log" 2>&1 &
sleep 2

# --- 5. noVNC web front-end (HTTP + WebSocket) --------------------------------
NOVNC_WEB="/usr/share/novnc"
log "Starting noVNC web server on port $WEB_PORT ..."
setsid websockify --web="$NOVNC_WEB" "$WEB_PORT" "localhost:$VNC_PORT" \
    </dev/null >"$LOG_DIR/websockify.log" 2>&1 &
sleep 2

# --- 6. launch Isaac Sim GUI on the virtual display ---------------------------
# NOTE: this is a SECOND Isaac (GUI) instance, separate from the container's
# headless one. Both share the GPU. If Vulkan can't present to Xvfb you'll see
# an error in isaac-gui.log — then we switch to VirtualGL (see README).
cd "$ISAAC_ROOT"
GUI_LAUNCHER=""
for cand in ./isaac-sim.sh ./runapp.sh ./kit/kit; do
    [[ -x "$cand" ]] && { GUI_LAUNCHER="$cand"; break; }
done
if [[ -z "$GUI_LAUNCHER" ]]; then
    log "WARNING: no GUI launcher found in $ISAAC_ROOT (looked for isaac-sim.sh / runapp.sh)."
    log "Desktop + VNC are up; start Isaac manually with DISPLAY=$DISPLAY_NUM."
else
    log "Launching Isaac Sim GUI ($GUI_LAUNCHER) on $DISPLAY_NUM ..."
    setsid env DISPLAY="$DISPLAY_NUM" "$GUI_LAUNCHER" --allow-root \
        </dev/null >"$LOG_DIR/isaac-gui.log" 2>&1 &
    echo $! > "$LOG_DIR/isaac-gui.pid"
fi

POD="${RUNPOD_POD_ID:-<POD_ID>}"
URL="https://${POD}-${WEB_PORT}.proxy.runpod.net/vnc.html?autoconnect=1&resize=remote"
echo "$URL" > "$LOG_DIR/novnc_url.txt"

echo ""
echo "=============================================================="
echo "  noVNC desktop is up. Open in your browser:"
echo "    $URL"
echo "  (saved to $LOG_DIR/novnc_url.txt)"
echo "  Isaac Sim GUI is starting on the virtual display — give it 1-2 min,"
echo "  then in the browser desktop use File > Open to load your scene."
echo "=============================================================="
echo ""
log "Logs: $LOG_DIR/  (xvfb, x11vnc, websockify, isaac-gui)"
log "Everything is detached (setsid) — survives terminal disconnect."
