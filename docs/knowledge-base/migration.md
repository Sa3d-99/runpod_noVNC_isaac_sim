# Gazebo separation

Commit `b924bd0` temporarily added ROS 2 Gazebo to this Isaac repository. At the user's request, Gazebo is now maintained separately in [Gazebo_ROS2_Web_Simulation](https://github.com/Sa3d-99/Gazebo_ROS2_Web_Simulation).

The Isaac application scripts (`bootstrap.sh`, `install.sh`, `novnc.sh`, `stop.sh`), `README.md`, `TEMPLATE.md`, and `requirements.txt` are restored byte-for-byte from `cfdca8f`. The Gazebo helper, Gazebo tests/CI, and Gazebo-specific notes/evidence are removed from the Isaac working tree. This is a forward commit; the combined commit remains in Git history.

The independent Gazebo repository receives the tested Gazebo helper, desktop flow, tests, compatibility decisions, and saved integration results. Those clean Docker results belong to the combined implementation at `b924bd0`; they are inherited evidence, not a fresh full integration test of the separated project.

Authored knowledge notes remain under `docs/knowledge-base/`; local Graphify and Obsidian outputs are updated for the restored Isaac source. Old authored vault material is retained as clearly marked historical material when applicable, rather than treated as current Isaac behavior.
