#!/usr/bin/env bash
# =============================================================================
# install.sh — install everything the noVNC method needs, inside the container.
#
# System packages (apt):
#   git         clone/update this repo on the pod
#   python3     runtime for websockify (the noVNC WebSocket bridge)
#   python3-pip installs requirements.txt
#   xvfb        the virtual X screen Isaac Sim renders into
#   x11vnc      exposes that screen as a VNC server
#   fluxbox     minimal window manager (so Isaac's window is placed/resizable)
#   novnc       the browser-side VNC client (HTML/JS served to you)
#   websockify  bridges noVNC's WebSocket to the VNC port
#   x11-utils   provides xdpyinfo, used to verify the display came up
#
# Python packages (pip): see requirements.txt
#
# Idempotent: skips apt entirely when everything is already present.
# novnc.sh calls this automatically — you rarely need to run it yourself.
# =============================================================================
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { echo "[install] $*"; }
die() { echo "[install] ERROR: $*" >&2; exit 1; }

# --- privilege check ------------------------------------------------------------
# Some RunPod Isaac images run as the unprivileged 'isaac-sim' user, where
# apt-get fails with "Permission denied". Use sudo when we're not root.
SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
    if sudo -n true 2>/dev/null; then
        SUDO="sudo"
        log "Not root — using passwordless sudo for package installs."
    else
        die "Not running as root and passwordless sudo is unavailable.
       Fix by either:
         (a) using a root shell:            sudo -i     then re-run
         (b) starting the pod as root, or
         (c) pre-installing the packages listed in requirements.txt.
       Current user: $(id -un)"
    fi
fi

# --- system packages ------------------------------------------------------------
MISSING=()
for cmd in git python3 Xvfb x11vnc fluxbox websockify xdpyinfo; do
    command -v "$cmd" >/dev/null 2>&1 || MISSING+=("$cmd")
done
# noVNC ships web assets, not a binary — check the directory instead
[[ -d /usr/share/novnc ]] || MISSING+=("novnc")

if [[ ${#MISSING[@]} -eq 0 ]]; then
    log "All system dependencies already present."
else
    log "Installing missing: ${MISSING[*]}"
    $SUDO apt-get update -qq
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        git \
        python3 python3-pip \
        xvfb x11vnc fluxbox \
        novnc websockify \
        x11-utils \
        ca-certificates >/dev/null
    log "System packages installed."
fi

# --- python packages ------------------------------------------------------------
# Only runs if requirements.txt lists a real (non-comment) package.
REQ="$DIR/requirements.txt"
if [[ -f "$REQ" ]] && grep -qEv '^[[:space:]]*(#|$)' "$REQ"; then
    log "Installing Python requirements..."
    python3 -m pip install --quiet --no-input -r "$REQ" 2>/dev/null \
        || python3 -m pip install --quiet --no-input --break-system-packages -r "$REQ"
    log "Python packages installed."
fi

log "Ready."
