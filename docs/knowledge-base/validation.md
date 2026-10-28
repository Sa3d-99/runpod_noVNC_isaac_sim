# Validation evidence

Recorded 2026-10-28. The project first restored the original Isaac runtime, then received user authorization for targeted lifecycle and startup fixes.

The restoration check compares `bootstrap.sh`, `install.sh`, `novnc.sh`, `stop.sh`, `README.md`, `TEMPLATE.md`, and `requirements.txt` byte-for-byte against `cfdca8f`. Bash syntax is checked with:

```bash
bash -n bootstrap.sh install.sh novnc.sh stop.sh
```

At separation, all seven restored files matched `cfdca8f` byte-for-byte and Bash syntax passed. This is historical baseline evidence, not a claim that the subsequently hardened runtime remains identical. `gazebo.sh`, `tests/test_gazebo.py`, and `.github/workflows/checks.yml` are absent. No new NVIDIA Isaac image/GPU rendering or actual RunPod proxy test is claimed.

Gazebo Docker results from the former combined implementation are preserved in the separate [Gazebo repository](https://github.com/Sa3d-99/Gazebo_ROS2_Web_Simulation). They do not establish runtime behavior of this restored checkout. The temporary test containers and newly pulled Ubuntu images were removed after those tests; separation requires no new Docker downloads or host ROS/Gazebo installation.

The local graph reflects current Isaac source without the deleted Gazebo implementation. Historical notes remain labelled as historical. Source-aware incremental updates and the graph integrity diagnostic completed without missing/dangling endpoints, self-loops, or collapsed edges.

## Deleted pod and targeted hardening

The user clarified that the earlier pod was deleted. Later authentication rejection and HTTP 404 cannot establish the original application failure; there is no live pod to repair. The first SSH closure remains uncorrelated with container System logs.

The latest request authorizes fixing code issues before the user creates a fresh pod. All 17 current unittest methods passed in 31.584 seconds. All five Bash scripts parse:

```bash
bash -n bootstrap.sh install.sh install-utils.sh novnc.sh stop.sh
python3 -m unittest discover -s tests -v
```

Eight process-controller tests use disposable real Linux sessions to verify legacy PID refusal, PID start-time reuse checks, boot/display/state guards, PID 1 and ancestor protection, owned descendant cleanup while unrelated processes survive, SIGKILL fallback for owned stubborn processes, and surviving descendants after their launcher exits.

Four startup tests run the actual shell scripts against mocked display/TCP services and a fake Isaac launcher. They cover `DISPLAY` and `--allow-root`, missing RunPod hostname fallback, repeated desktop-only startup, refusing an unverified occupied display, scoped stop, and printing early GUI failure logs. This does not render NVIDIA Isaac Sim.

The remaining five methods cover visible bootstrap download/scratch cleanup and installer output/error/cache/serialization behavior. Simulated default-cache deletion leaves the private apt archive usable; pip/package failures remain visible in terminal/log output and retain failure status. No real packages are installed by these fixtures.

No new OS/Docker/Gazebo downloads or actual Isaac/GPU/container/RunPod rendering test was performed. The pod was deleted, so the user must validate a fresh deployment; local regression success does not establish a remote repair or explain the original SSH closure.
