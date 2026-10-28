# Architecture

The shared desktop remains the original project's execution path. `SIMULATOR=isaac` is the default; `SIMULATOR=gazebo` selects a second application on the same desktop.

```text
bootstrap.sh → novnc.sh → install.sh
                  │           └─ gazebo.sh helpers when Gazebo is selected
                  ├─ Xvfb + Fluxbox
                  ├─ x11vnc on localhost:5900
                  ├─ websockify + noVNC on HTTP :8080 → RunPod proxy → browser
                  └─ Isaac GUI OR ROS launch → Gazebo GUI/server
```

`bootstrap.sh` downloads a GitHub archive without requiring Git, replaces the destination checkout, and executes `novnc.sh`. Environment overrides pass through. Avoid storing unique work inside a bootstrap-managed destination, because rerunning bootstrap replaces it.

`install.sh` installs the existing apt desktop stack and `requirements.txt` (`websockify`). Installation requires root or passwordless sudo. In Gazebo mode, compatibility is checked first and Gazebo/ROS packages are then installed through the shared helper. Isaac mode does not install ROS or Gazebo.

`novnc.sh` cleans up its previous desktop, exports the selected X display, starts Xvfb, Fluxbox, x11vnc, and websockify, and launches the selected simulator. Long-lived processes use `setsid` so terminal disconnects do not own their lifetime. Isaac retains its existing launcher discovery (`isaac-sim.sh`, `runapp.sh`, selector, then Kit fallback), `ISAAC_ROOT`, and `NO_ISAAC=1` behavior.

Gazebo uses a separate detached ROS launch session and `gazebo-gui.pid`. Before a restart or through `stop.sh`, the helper stops the recorded Gazebo process group. Other Gazebo sessions are not selected by a broad name match. Existing Isaac shutdown logic is preserved; its PID tracking and GUI process patterns are separate from Gazebo.

Defaults are display `:1`, resolution `1920x1080`, VNC `5900`, HTTP `8080`, and logs `/workspace/novnc-logs`. The browser URL is printed and saved to `novnc_url.txt` when a RunPod pod identifier is available; otherwise the script gives console instructions. VNC authentication is optional through `VNC_PASSWORD`.

`stop.sh` stops the desktop and launched application without stopping the pod. Stopping billing remains a RunPod console action. The historical container-main-process warning remains relevant when using the original Isaac image; do not turn it into a blanket statement about unrelated images.

See [Gazebo decisions](gazebo.md) and [validation evidence](validation.md). Exact environment variables and launch commands are in the main [README](../../README.md).
