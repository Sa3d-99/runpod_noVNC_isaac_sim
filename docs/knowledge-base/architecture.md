# Architecture

This repository runs Isaac Sim's GUI through a browser desktop on RunPod. The application was restored from `cfdca8f` at separation; the user subsequently authorized targeted lifecycle, startup, and installer hardening. Gazebo remains a separate [project](https://github.com/Sa3d-99/Gazebo_ROS2_Web_Simulation).

```text
bootstrap.sh → novnc.sh → install.sh → install-utils.sh
                  └─ process_control.py
                       ├─ Xvfb + Fluxbox
                       ├─ x11vnc on localhost:5900
                       ├─ websockify + noVNC on HTTP :8080 → RunPod proxy → browser
                       └─ Isaac Sim GUI
```

`bootstrap.sh` downloads the repository archive with visible progress, replaces its destination checkout, removes download scratch files, and executes `novnc.sh`. Keep unique work outside the bootstrap-managed checkout.

`install.sh` installs desktop dependencies and `websockify`; root or passwordless sudo is required. Output remains visible and is appended to `LOG_DIR/install.log`. `install-utils.sh` serializes this project's installers, supplies a private temporary apt archive/partial directory, preserves apt/dpkg locks, enables three retries and a 300-second package-lock timeout, and cleans up its temporary cache. Failures retain a nonzero result and block desktop startup. No ROS or Gazebo packages are installed.

`novnc.sh` requires the full repository and uses a stack lock while cleaning up and starting services. All desktop/GUI launches go through `process_control.py`, which creates detached Linux sessions and component logs. State lives under `LOG_DIR/.processes/display-<number>/` in private directories and mode-600 JSON files. Records contain an owner marker, display, boot ID, PID, process start ticks, and a random inherited session token.

Cleanup verifies the recorded process lifetime/session/token before signalling owned session members. Descendants can remain identifiable after a launcher exits. PID 1, the controller, and calling-shell ancestors are protected. Legacy `.pid` files remain informational and do not authorize a kill. `stop.sh` delegates to the controller under the stack lock; global process-name matches and X socket deletion are removed. Startup refuses an occupied unverified display or port instead of adopting or stopping it.

Isaac launcher discovery remains `isaac-sim.sh`, `runapp.sh`, selector, then Kit fallback. `ISAAC_ROOT` locates the installation; `NO_ISAAC=1` starts only the desktop. A GUI that exits during startup has its log printed while the browser desktop remains available. Missing RunPod identifier/hostname variables now lead to console instructions rather than an unset-variable failure.

Defaults remain display `:1`, resolution `1920x1080`, VNC `5900`, HTTP `8080`, and logs `/workspace/novnc-logs`. VNC authentication is optional through `VNC_PASSWORD`. Stopping this desktop does not stop pod billing.

Historical image, GPU, and networking observations in the original documentation are not a new deployment test. See [validation](validation.md), [connection investigation](ssh-terminal-investigation.md), and [separation provenance](migration.md).
