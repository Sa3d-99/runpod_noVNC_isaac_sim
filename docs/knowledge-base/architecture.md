# Architecture

This repository runs Isaac Sim's GUI through a browser desktop on RunPod. The runtime scripts, `README.md`, `TEMPLATE.md`, and `requirements.txt` are restored from `cfdca8f`; Gazebo has moved to its own [repository](https://github.com/Sa3d-99/Gazebo_ROS2_Web_Simulation).

```text
bootstrap.sh → novnc.sh → install.sh
                  ├─ Xvfb + Fluxbox
                  ├─ x11vnc on localhost:5900
                  ├─ websockify + noVNC on HTTP :8080 → RunPod proxy → browser
                  └─ Isaac Sim GUI
```

`bootstrap.sh` downloads a GitHub archive without requiring Git, replaces the destination checkout, and executes `novnc.sh`. Environment overrides pass through. Keep unique work outside a bootstrap-managed destination because rerunning bootstrap replaces it.

`install.sh` installs apt desktop dependencies and `requirements.txt` (`websockify`). Installation requires root or passwordless sudo. No ROS or Gazebo package installation belongs to this project.

`novnc.sh` cleans up its previous desktop, exports the selected X display, starts Xvfb, Fluxbox, x11vnc, and websockify, and discovers an Isaac launcher (`isaac-sim.sh`, `runapp.sh`, selector, then Kit fallback). Long-lived processes use `setsid`. `ISAAC_ROOT` locates the installation; `NO_ISAAC=1` starts only the desktop.

Defaults remain display `:1`, resolution `1920x1080`, VNC `5900`, HTTP `8080`, and logs `/workspace/novnc-logs`. The script prints and saves the browser URL when a RunPod pod identifier is present. Authentication remains optional through `VNC_PASSWORD`.

`stop.sh` uses its Isaac PID file and existing GUI/desktop process patterns. It does not stop pod billing. The original warning about preserving the container's main Isaac process remains documented. Historical image, GPU, and networking claims in `README.md`, `TEMPLATE.md`, and `POSTMORTEM.md` have not been freshly verified by the source restoration.

Restoration also retains original implementation details, including the unset-hostname fallback and colon-delimited desktop-stop patterns; fixes from the temporary combined project were not silently retained. See [validation](validation.md) and [migration](migration.md).
