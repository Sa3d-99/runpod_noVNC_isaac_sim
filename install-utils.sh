#!/usr/bin/env bash
# Shared installer output and apt configuration. Sourcing this file changes nothing.

install_log() { echo "[install] $*"; }

install_cleanup() {
    local result=$?
    if [[ -n "${INSTALL_APT_CACHE:-}" && -d "$INSTALL_APT_CACHE" ]]; then
        ${SUDO:-} rm -rf -- "$INSTALL_APT_CACHE"
    fi
    if [[ "$result" -ne 0 ]]; then
        install_log "Installation stopped (exit $result). See ${LOG_DIR}/install.log."
        install_log "Rerun bash install.sh to finish; the desktop starts only after installation succeeds."
    fi
    return "$result"
}

install_prepare_apt() {
    # Serialize this project's installers; keep apt/dpkg's own locks enabled too.
    install_log "Waiting for any other Isaac installer to finish (up to 5 minutes)..."
    exec {INSTALL_LOCK_FD}>"${TMPDIR:-/tmp}/isaac-web-install.lock"
    flock -w 300 "$INSTALL_LOCK_FD" || {
        install_log "Another Isaac installer is still running. Let it finish before retrying."
        return 1
    }
    # Some container hooks clean /var/cache/apt/archives. A private download
    # directory prevents those hooks from removing this install's partial .debs.
    INSTALL_APT_CACHE="$(mktemp -d "${TMPDIR:-/tmp}/isaac-web-apt.XXXXXX")"
    chmod 755 "$INSTALL_APT_CACHE"
    mkdir -p "$INSTALL_APT_CACHE/partial"
    trap install_cleanup EXIT
    trap 'install_log "Interrupted. Installation is incomplete."; exit 130' INT
    trap 'install_log "Terminated. Installation is incomplete."; exit 143' TERM
    install_log "Using a private apt download directory: $INSTALL_APT_CACHE"
}

install_apt() {
    install_log "Running apt-get $* (downloads and package progress follow)..."
    # quiet=0 overrides quiet defaults in container apt configuration. Do not use
    # --fix-missing: it can hold back packages while appearing to finish.
    ${SUDO:-} env DEBIAN_FRONTEND=noninteractive apt-get \
        -o quiet=0 -o Acquire::Retries=3 -o DPkg::Lock::Timeout=300 \
        -o Dpkg::Use-Pty=0 -o APT::Color=0 \
        -o "Dir::Cache::archives=$INSTALL_APT_CACHE/" "$@" </dev/null
}
