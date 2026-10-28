#!/usr/bin/env bash
# Gazebo helpers shared by install.sh, novnc.sh and stop.sh.
# Source this file for functions, or run: bash gazebo.sh check|install|launch|stop

gazebo_log() { echo "[gazebo] $*"; }
gazebo_error() { echo "[gazebo] ERROR: $*" >&2; return 1; }

gazebo_select_platform() {
    local ID="" VERSION_ID="" expected=""
    # An optional fixture path is used by the compatibility tests.
    local release_file="${1:-/etc/os-release}"
    [[ -r "$release_file" ]] || { gazebo_error "Cannot read $release_file"; return 1; }
    # shellcheck disable=SC1090
    source "$release_file"
    case "${ID}:${VERSION_ID}" in
        ubuntu:22.04) expected=humble; GAZEBO_RELEASE=Fortress; GAZEBO_CODENAME=jammy ;;
        ubuntu:24.04) expected=jazzy; GAZEBO_RELEASE=Harmonic; GAZEBO_CODENAME=noble ;;
        *) gazebo_error "Gazebo supports only Ubuntu 22.04 / ROS Humble or Ubuntu 24.04 / ROS Jazzy (found ${ID} ${VERSION_ID})."; return 1 ;;
    esac
    if [[ -n "${ROS_DISTRO:-}" && "$ROS_DISTRO" != "$expected" ]]; then
        gazebo_error "Ubuntu ${VERSION_ID} requires ROS ${expected}; ROS_DISTRO=${ROS_DISTRO} is unsupported."
        return 1
    fi
    export ROS_DISTRO="$expected"
}

gazebo_package_installed() {
    [[ "$(dpkg-query -W -f='${Status}' "$1" 2>/dev/null)" == 'install ok installed' ]]
}

gazebo_install() {
    gazebo_select_platform || return 1
    local packages=("ros-${ROS_DISTRO}-ros-base" "ros-${ROS_DISTRO}-ros-gz"
        libgl1-mesa-dri libglx-mesa0 libegl1 libxcb-cursor0 dbus-x11)
    local package missing=0
    for package in "${packages[@]}"; do
        gazebo_package_installed "$package" || missing=1
    done
    if [[ "$missing" == 0 ]]; then
        gazebo_log "ROS ${ROS_DISTRO} + Gazebo ${GAZEBO_RELEASE} already installed."
        return 0
    fi

    gazebo_log "Installing ROS ${ROS_DISTRO} + Gazebo ${GAZEBO_RELEASE}..."
    ${SUDO:-} apt-get update -qq
    ${SUDO:-} env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        ca-certificates curl python3 software-properties-common >/dev/null
    ${SUDO:-} add-apt-repository -y universe >/dev/null

    # Use ROS's maintained repository/key package. Existing ROS images may already
    # have a working repository; leave that configuration in place when usable.
    ${SUDO:-} apt-get update -qq
    if ! apt-cache show "ros-${ROS_DISTRO}-ros-gz" >/dev/null 2>&1; then
        local source_version tmp_dir
        source_version="$(curl -fsSL --retry 3 \
            https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
            | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')"
        [[ "$source_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
            || { gazebo_error "Could not determine ros2-apt-source release."; return 1; }
        tmp_dir="$(mktemp -d)"
        if ! curl -fsSL --retry 3 -o "$tmp_dir/ros2-apt-source.deb" \
            "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${source_version}/ros2-apt-source_${source_version}.${GAZEBO_CODENAME}_all.deb"; then
            rm -rf "$tmp_dir"
            gazebo_error "Could not download ros2-apt-source."
            return 1
        fi
        if ! ${SUDO:-} dpkg -i "$tmp_dir/ros2-apt-source.deb"; then
            rm -rf "$tmp_dir"
            return 1
        fi
        rm -rf "$tmp_dir"
    fi
    ${SUDO:-} apt-get update -qq
    ${SUDO:-} env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${packages[@]}"
    gazebo_log "ROS ${ROS_DISTRO} + Gazebo ${GAZEBO_RELEASE} ready."
}

gazebo_launch() {
    gazebo_select_platform || return 1
    local setup="/opt/ros/${ROS_DISTRO}/setup.bash"
    [[ -f "$setup" ]] || { gazebo_error "Missing $setup; run SIMULATOR=gazebo bash install.sh first."; return 1; }
    # ROS setup scripts may reference unset variables. Restore nounset afterwards.
    set +u
    # shellcheck disable=SC1090
    source "$setup"
    set -u
    export DISPLAY="${DISPLAY:-${DISPLAY_NUM:-:1}}"
    export QT_X11_NO_MITSHM=1
    export QT_QPA_PLATFORM=xcb
    export LANG="${LANG:-C.UTF-8}"
    gazebo_log "Launching ${GAZEBO_RELEASE} with ROS ${ROS_DISTRO} on ${DISPLAY}."
    exec ros2 launch ros_gz_sim gz_sim.launch.py \
        "gz_args:=${GAZEBO_ARGS:--r shapes.sdf}" on_exit_shutdown:=true
}

gazebo_stop() {
    local pid_file="${LOG_DIR:-/workspace/novnc-logs}/gazebo-gui.pid"
    [[ -f "$pid_file" ]] || return 0
    local pid
    pid="$(cat "$pid_file")"
    # novnc.sh starts a separate session. Signal only our recorded group so ROS
    # launch can shut down its server and GUI, leaving other simulations alone.
    if [[ "$pid" =~ ^[0-9]+$ && "$pid" -gt 1 ]] && kill -0 -- "-$pid" 2>/dev/null; then
        gazebo_log "Stopping Gazebo session $pid..."
        kill -INT -- "-$pid" 2>/dev/null || true
        for _ in {1..10}; do
            kill -0 -- "-$pid" 2>/dev/null || break
            sleep 1
        done
        kill -TERM -- "-$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    set -euo pipefail
    case "${1:-check}" in
        check) gazebo_select_platform; gazebo_log "Ubuntu ${GAZEBO_CODENAME}: ROS ${ROS_DISTRO} + Gazebo ${GAZEBO_RELEASE}" ;;
        install) exec env SIMULATOR=gazebo bash "$(dirname "${BASH_SOURCE[0]}")/install.sh" ;;
        launch) gazebo_launch ;;
        stop) gazebo_stop ;;
        *) gazebo_error "Usage: bash gazebo.sh check|install|launch|stop"; exit 1 ;;
    esac
fi
