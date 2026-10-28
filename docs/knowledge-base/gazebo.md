# Gazebo compatibility and decisions

The implementation reads the container's `/etc/os-release` and accepts only:

| Container OS | ROS distro | Gazebo release |
|---|---|---|
| Ubuntu 22.04 / Jammy | Humble | Fortress |
| Ubuntu 24.04 / Noble | Jazzy | Harmonic |

An unset `ROS_DISTRO` is filled from the Ubuntu version. A conflicting distro or any other operating system/version is rejected before apt installation or desktop cleanup. The host OS does not determine compatibility. Pairings follow the [Gazebo ROS installation guide](https://gazebosim.org/docs/latest/ros_installation/) referenced in the project README.

`gazebo.sh` contains sourceable compatibility, installation, launch, and shutdown helpers, plus `check`, `install`, `launch`, and `stop` commands. `install.sh`, `novnc.sh`, and `stop.sh` reuse these helpers. This preserves the original desktop flow and avoids creating a second VNC stack.

Installation uses `ros-<distro>-ros-base` and `ros-<distro>-ros-gz` with Mesa/GL, Qt/XCB, and D-Bus dependencies. Existing installed packages and a usable ROS apt source are reused. If ROS packages cannot be found, the installer configures the maintained `ros2-apt-source` release package. No separate Gazebo Classic installation or OSRF repository is added.

Launch sources `/opt/ros/<distro>/setup.bash`, selects Qt's XCB platform, and runs `ros2 launch ros_gz_sim gz_sim.launch.py` against the shared X display. `GAZEBO_ARGS` defaults to `-r shapes.sdf` and can select another world. The ROS launch shutdown option and tracked process-group signals allow the GUI and simulation server to stop together.

The project installs ROS/Gazebo integration packages but does not invent a topic bridge for a user's robot. A world-specific `ros_gz_bridge` configuration remains an explicit user action. `LIBGL_ALWAYS_SOFTWARE=1` is a documented rendering fallback when the virtual display cannot use available graphics drivers.

Gazebo logs and the session PID are stored alongside existing desktop logs, under `LOG_DIR`. `bash gazebo.sh stop` keeps the browser desktop open; `bash stop.sh` stops both. `NO_ISAAC` applies to Isaac mode.

See [validation](validation.md) for evidence and remaining runtime checks.
