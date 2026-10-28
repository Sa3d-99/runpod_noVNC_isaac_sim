#!/usr/bin/env bash
# =============================================================================
# bootstrap.sh — one command, zero prerequisites, fully automatic.
#
# Fetches this repo WITHOUT git (a fresh RunPod Isaac pod has no git, and may run
# as the unprivileged 'isaac-sim' user where apt needs sudo), then runs novnc.sh.
#
# Use it directly from a fresh pod — nothing to install first:
#
#   curl -fsSL https://raw.githubusercontent.com/Sa3d-99/runpod_noVNC_isaac_sim/main/bootstrap.sh | bash
#
# Or as the RunPod "Container Start Command" for a pod that comes up ready:
#
#   bash -c "curl -fsSL https://raw.githubusercontent.com/Sa3d-99/runpod_noVNC_isaac_sim/main/bootstrap.sh | bash; sleep infinity"
#
# Env overrides are passed straight through to novnc.sh (WEB_PORT, RES,
# VNC_PASSWORD, ...). Re-running is safe: it re-downloads and restarts cleanly.
# =============================================================================
set -euo pipefail

REPO="${REPO:-Sa3d-99/runpod_noVNC_isaac_sim}"
BRANCH="${BRANCH:-main}"
DEST="${DEST:-/workspace/runpod_noVNC_isaac_sim}"

log() { echo "[bootstrap] $*"; }
die() { echo "[bootstrap] ERROR: $*" >&2; exit 1; }

# --- fetch the repo without git -------------------------------------------------
command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1 \
    || die "neither curl nor wget is available — cannot download the repo."

TARBALL="https://codeload.github.com/${REPO}/tar.gz/refs/heads/${BRANCH}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

log "Downloading ${REPO}@${BRANCH} (no git required)..."
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$TARBALL" -o "$TMP/repo.tar.gz" || die "download failed: $TARBALL"
else
    wget -qO "$TMP/repo.tar.gz" "$TARBALL" || die "download failed: $TARBALL"
fi

tar -xzf "$TMP/repo.tar.gz" -C "$TMP" || die "could not extract the archive."
SRC="$(find "$TMP" -maxdepth 1 -type d -name '*-'"${BRANCH}" | head -1)"
[[ -n "$SRC" ]] || die "unexpected archive layout."

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
mv "$SRC" "$DEST"
chmod +x "$DEST"/*.sh 2>/dev/null || true
log "Installed to $DEST"

# --- run the method -------------------------------------------------------------
cd "$DEST"
exec bash ./novnc.sh
