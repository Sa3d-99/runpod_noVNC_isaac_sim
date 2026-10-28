# Validation evidence

Recorded 2026-10-28. Source and unit checks cover behavior without modifying the developer host's ROS or desktop installation.

```bash
bash -n bootstrap.sh install.sh novnc.sh gazebo.sh stop.sh
python3 -m unittest discover -s tests -v
```

Six unittest methods pass. They cover both supported compatibility pairs and automatic distro selection; mismatches and unsupported distros; unsupported operating systems; invalid simulator selection before apt/desktop commands; shutdown of the recorded session while an unrelated process survives; and missing, stale, or invalid PID files.

`.github/workflows/checks.yml` runs Bash syntax and these tests on Ubuntu 22.04 and 24.04. Defining the workflow does not establish that a hosted CI run has completed.

Clean Docker integration tests passed on both supported pairs: Ubuntu 22.04 / ROS Humble / Gazebo Fortress and Ubuntu 24.04 / ROS Jazzy / Gazebo Harmonic. Both installed the desktop and ROS/Gazebo packages from scratch using the official `ros2-apt-source` 1.3.0 package.

| Check | Humble / Fortress | Jazzy / Harmonic |
|---|---|---|
| noVNC `/vnc.html` returns HTTP 200 and noVNC content | Pass | Pass |
| Gazebo window mapped; screenshot shows the colored shapes world | Pass | Pass |
| World clock, state, stats, and scene topics present | Pass | Pass |
| Wrong ROS distro rejected while the existing desktop stays up | Pass | Pass |
| `gazebo.sh stop` stops ROS/Gazebo and keeps noVNC available | Pass | Pass |
| Restart reuses installed packages and restores GUI/topics/HTTP | Pass | Pass |
| `stop.sh` stops Gazebo and all live desktop stack processes | Pass | Pass |

On Ubuntu 22.04, a stub Isaac launcher also confirmed `DISPLAY=:1` and `--allow-root`; this was not a real Isaac rendering test. `NO_ISAAC=1` desktop mode and URL fallback without RunPod environment variables passed.

The [saved integration results](evidence/gazebo-integration-2026-10-28.json) preserve both result records and cleanup scope. Test containers `runpod-gazebo-humble-check` and `runpod-gazebo-jazzy-check`, their apt/Gazebo installations, and the newly downloaded `ubuntu:22.04` and `ubuntu:24.04` images were removed after validation. Exact-name Docker listings confirmed none remained. No global prune was run, and preexisting host ROS/Gazebo, containers, and images were left alone.

Native Isaac rendering on its NVIDIA image/GPU and access through an actual RunPod proxy were not tested. Local HTTP, X display rendering, and simulator topic checks establish container behavior, not external RunPod networking.

The local Graphify graph is generated from source AST and host-agent semantic extraction. Its integrity diagnostic found no missing/dangling endpoints, self-loops, or collapsed edges. Original postmortem claims remain identified as historical observations; inferred relationships must be labelled rather than presented as source facts. Token usage for host-agent extraction is unavailable and is identified as such in the report; no paid extraction API was used.
