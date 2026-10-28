# Validation evidence

Recorded 2026-10-28. This change restores the original Isaac runtime instead of adding simulator features.

The restoration check compares `bootstrap.sh`, `install.sh`, `novnc.sh`, `stop.sh`, `README.md`, `TEMPLATE.md`, and `requirements.txt` byte-for-byte against `cfdca8f`. Bash syntax is checked with:

```bash
bash -n bootstrap.sh install.sh novnc.sh stop.sh
```

All seven restored files match `cfdca8f` byte-for-byte. Bash syntax passes. `gazebo.sh`, `tests/test_gazebo.py`, and `.github/workflows/checks.yml` are absent. No new NVIDIA Isaac image/GPU rendering or actual RunPod proxy test is claimed.

Gazebo Docker results from the former combined implementation are preserved in the separate [Gazebo repository](https://github.com/Sa3d-99/Gazebo_ROS2_Web_Simulation). They do not establish runtime behavior of this restored checkout. The temporary test containers and newly pulled Ubuntu images were removed after those tests; separation requires no new Docker downloads or host ROS/Gazebo installation.

The local graph is refreshed from current source with deleted Gazebo nodes pruned. Historical notes remain labelled as historical. Source-aware incremental updates and the graph integrity diagnostic completed without missing/dangling endpoints, self-loops, or collapsed edges.
