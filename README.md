# Support

## If this tool saved you time and server costs, consider supporting my work here: [Buy me a coffee](https://buymeacoffee.com/sa3d_99)

---

# Isaac Sim and ROS 2 Gazebo on RunPod via noVNC

Run NVIDIA Isaac Sim on a RunPod pod and use its **full GUI in your browser**.
Works on **all Isaac Sim versions** (4.0 → 5.x). No UDP, no WebRTC, no ICE, no
TURN, no Direct-TCP ports — one HTTP port and you're done.

The same browser desktop can also run **Gazebo with ROS 2**. Isaac Sim remains
the default; select Gazebo with `SIMULATOR=gazebo`.

## Choose what to run

Expose port **8080 as HTTP** in your RunPod pod. Installation needs **root or
passwordless sudo**, a writable system, and internet access. Ubuntu means the
OS **inside the container**, regardless of the host's OS.

| Simulator | Container OS / image | ROS 2 | Gazebo |
|---|---|---|---|
| Isaac Sim (default) | `nvcr.io/nvidia/isaac-sim:4.0.0` | Not required | Not installed |
| Gazebo | Ubuntu **22.04**, e.g. `ubuntu:22.04` | **Humble** | **Fortress** |
| Gazebo | Ubuntu **24.04**, e.g. `ubuntu:24.04` | **Jazzy** | **Harmonic** |

Gazebo mode accepts **only these two Ubuntu/ROS combinations** and rejects other
versions or mismatches before installing anything. If `ROS_DISTRO` is omitted,
it selects Humble on 22.04 and Jazzy on 24.04. These are the
[official ROS/Gazebo pairings](https://gazebosim.org/docs/latest/ros_installation/).

- **Isaac Sim:** use the ready-made template or the Isaac command below.
- **ROS Humble + Gazebo:** use [the Ubuntu 22.04 commands](#gazebo--ros-humble-on-ubuntu-2204).
- **ROS Jazzy + Gazebo:** use [the Ubuntu 24.04 commands](#gazebo--ros-jazzy-on-ubuntu-2404).

The published Isaac template below still launches Isaac Sim. For Gazebo, create
a pod with the matching Ubuntu image and the start command in the Gazebo section.

## Easiest way — deploy the ready-made template

A public RunPod template is already set up with everything below. **Nothing to
install, nothing to configure.**

### 👉 [**Deploy: Isaac-Sim-Official**](https://console.runpod.io/deploy?template=4qyomso891)

Or find it manually: RunPod → **Templates** → search **`Isaac-Sim-Official`**
(template id `4qyomso891`).

1. **Pick an RTX 4090.** (RTX 50-series does **not** work — see below.)
2. **Deploy.** Wait ~2–3 minutes for boot + Isaac Sim to load.
3. **Connect → HTTP Service → port 8080.**

The Isaac Sim desktop opens in your browser. Load your scene with
**File → Open**. Done.

> Building your own template instead? The exact settings are in
> [TEMPLATE.md](TEMPLATE.md).

### ⚠️ GPU: use an RTX 4090, not a 5080/5090

Isaac Sim 4.0.0 predates the RTX 50-series (Blackwell, compute capability 12.0).
On a 5080/5090 it logs `unsupported by this version` and the viewport never
renders — a grey window, no matter how healthy the desktop is. Ada/Ampere cards
(**RTX 4090**, 3090, A6000, L40S) work.

Blackwell support needs Isaac 4.5+/5.x/6.x — but those images run as an
unprivileged user with no sudo and a read-only `/usr`, so the desktop can't be
installed there. **RTX 4090 + Isaac 4.0.0 is the combination that works.**

## Isaac Sim — manual install

If you're on your own pod rather than the template:

```bash
curl -fsSL https://raw.githubusercontent.com/Sa3d-99/runpod_noVNC_isaac_sim/main/bootstrap.sh | bash
```

Downloads the repo (no git needed), installs every dependency, starts the
desktop, launches Isaac Sim, and **prints your real URL** — no placeholder to
fill in. It's also saved to `/workspace/novnc-logs/novnc_url.txt`.

**Requirements:** port **8080** exposed as an **HTTP** port, and an Isaac image
that runs as **root** — use `nvcr.io/nvidia/isaac-sim:4.0.0`. Isaac 5.x/6.x
images run as an unprivileged user with no sudo and a read-only `/usr`, so
nothing can be installed there and the desktop can't start.

Already have the repo on the pod?

```bash
cd /workspace/runpod_noVNC_isaac_sim && bash novnc.sh
```

## Gazebo — ROS Humble on Ubuntu 22.04

Use an **Ubuntu 22.04** container. Start from an existing ROS Humble image or a
plain `ubuntu:22.04` image; the installer adds ROS and Gazebo when missing.
Minimal Ubuntu images need curl first:

```bash
apt-get update && apt-get install -y curl ca-certificates
```

**First start** (download, install and open Gazebo Fortress in noVNC):

```bash
curl -fsSL https://raw.githubusercontent.com/Sa3d-99/runpod_noVNC_isaac_sim/main/bootstrap.sh | SIMULATOR=gazebo ROS_DISTRO=humble bash
```

**Restart with the downloaded repo:**

```bash
cd /workspace/runpod_noVNC_isaac_sim
SIMULATOR=gazebo ROS_DISTRO=humble bash novnc.sh
```

## Gazebo — ROS Jazzy on Ubuntu 24.04

Use an **Ubuntu 24.04** container. Start from an existing ROS Jazzy image or a
plain `ubuntu:24.04` image. Minimal Ubuntu images need curl first:

```bash
apt-get update && apt-get install -y curl ca-certificates
```

**First start** (download, install and open Gazebo Harmonic in noVNC):

```bash
curl -fsSL https://raw.githubusercontent.com/Sa3d-99/runpod_noVNC_isaac_sim/main/bootstrap.sh | SIMULATOR=gazebo ROS_DISTRO=jazzy bash
```

**Restart with the downloaded repo:**

```bash
cd /workspace/runpod_noVNC_isaac_sim
SIMULATOR=gazebo ROS_DISTRO=jazzy bash novnc.sh
```

### Using Gazebo (both versions)

Open **RunPod → Connect → HTTP Service → port 8080**. The script prints and
saves your browser URL just as it does for Isaac Sim. Gazebo starts with its
bundled `shapes.sdf` world; first-time package installation can take several
minutes. Isaac Sim is not required in Gazebo mode.

```bash
# Check the Ubuntu/ROS pairing without installing anything
bash gazebo.sh check

# Install dependencies without starting the desktop
SIMULATOR=gazebo bash install.sh

# Start another world (paths with spaces need quotes inside GAZEBO_ARGS)
SIMULATOR=gazebo GAZEBO_ARGS='-r /workspace/worlds/my_world.sdf' bash novnc.sh

# If Gazebo reports graphics errors on the virtual display, try Mesa software rendering
SIMULATOR=gazebo LIBGL_ALWAYS_SOFTWARE=1 bash novnc.sh

# Inspect Gazebo startup
tail -50 /workspace/novnc-logs/gazebo-gui.log
```

ROS's `ros_gz` packages are installed for communication with Gazebo. Source ROS
in a separate SSH terminal to use its CLI (choose the matching distro):

```bash
source /opt/ros/humble/setup.bash   # Ubuntu 22.04
# OR:
source /opt/ros/jazzy/setup.bash    # Ubuntu 24.04
ros2 topic list
```

Robot topics need a `ros_gz_bridge` configuration for your simulation. Starting
Gazebo alone does not automatically bridge every Gazebo topic into ROS.

To start Gazebo on every pod boot, set the **Container Start Command** below.
The Ubuntu version selects the matching ROS distro automatically:

```bash
bash -c "apt-get update && apt-get install -y curl ca-certificates && curl -fsSL https://raw.githubusercontent.com/Sa3d-99/runpod_noVNC_isaac_sim/main/bootstrap.sh | SIMULATOR=gazebo bash; sleep infinity"
```

## Stopping either simulator

```bash
cd /workspace/runpod_noVNC_isaac_sim && bash stop.sh
```

Stops the desktop and the simulator this project launched, and leaves the pod
running. Restart Isaac with `bash novnc.sh`, or Gazebo with
`SIMULATOR=gazebo bash novnc.sh` on the matching Ubuntu container.

To stop only this project's Gazebo session while keeping the desktop open:

```bash
bash gazebo.sh stop
```

`stop.sh` deliberately leaves the container's *own* Isaac process alone — that
one is the container's main process, and killing it would stop the whole pod.

**To stop paying, stop the POD itself** in the RunPod console. `stop.sh` only
shuts down the desktop inside the pod; the pod keeps billing until you stop or
terminate it.

## How it works

```
Isaac Sim / Gazebo GUI  →  renders into a virtual X screen (Xvfb)
                        ↓
                   x11vnc  exposes that screen as VNC on localhost:5900
                        ↓
               websockify + noVNC  serve it as a web page on :8080
                        ↓
         RunPod HTTP proxy (TCP)  →  your browser
```

Isaac Sim never streams anything itself, and is never modified. We let it draw
its normal GUI into a virtual screen and ship those pixels over HTTP — the one
thing RunPod's network does well.

## Why Isaac's own streaming can't work on RunPod

| | Isaac WebRTC / native streaming | noVNC (this repo) |
|---|---|---|
| Transport | **UDP** (SRTP media) + ICE | **TCP** (HTTP + WebSocket) |
| RunPod support | ❌ no inbound UDP at all, ever | ✅ exactly what the HTTP proxy carries |
| Needs reachable public IPs | ✅ — but Isaac only advertises `127.0.0.1` / `172.18.0.2` | ❌ irrelevant |
| Ports to expose | 3+ Direct TCP ports, remapped every restart | 1 HTTP port (already there) |
| Isaac version differences | config keys move, and were removed in 5.x | ❌ none — Isaac isn't touched |
| Load your own scene | ❌ | ✅ full mouse/keyboard |

The full investigation — every approach tried, the exact failure of each, and why
noVNC wins — is in **[POSTMORTEM.md](POSTMORTEM.md)**.

## Isaac Sim — automatic on pod boot

RunPod console → Edit Pod → **Container Start Command**:

```bash
bash -c "curl -fsSL https://raw.githubusercontent.com/Sa3d-99/runpod_noVNC_isaac_sim/main/bootstrap.sh | bash; sleep infinity"
```

That's the whole thing. No git, no root assumption, nothing to pre-install — it
downloads, installs, and starts the desktop on every boot. Pod start =
browser-ready Isaac Sim, and the URL is waiting in
`/workspace/novnc-logs/novnc_url.txt`.

The `sleep infinity` keeps the container alive after the script detaches.

## Options

```bash
WEB_PORT=8080          # HTTP port noVNC is served on (must be exposed as HTTP)
RES=1920x1080          # virtual screen resolution
VNC_PASSWORD=secret    # add a VNC password (default: none — pod is private)
NO_ISAAC=1             # bring up the desktop only, launch Isaac yourself
ISAAC_ROOT=/isaac-sim  # where Isaac lives
SIMULATOR=isaac        # isaac (default) or gazebo
ROS_DISTRO=humble      # Gazebo: humble on 22.04, jazzy on 24.04; auto if unset
GAZEBO_ARGS='-r shapes.sdf' # Gazebo world and flags
```

Example: `RES=2560x1440 VNC_PASSWORD=hunter2 bash novnc.sh`

`NO_ISAAC` and `ISAAC_ROOT` apply to Isaac mode. Gazebo uses its own launcher
and writes `gazebo-gui.log` and `gazebo-gui.pid` under `LOG_DIR`.

## Troubleshooting

Everything is detached (`setsid`) — SSH/terminal drops will **not** kill it.

```bash
# is the whole stack up?
ss -ltn | grep -E ':(5900|8080) '        # VNC + noVNC listening
pgrep -af 'Xvfb|x11vnc|websockify'       # display + VNC + web
tail -20 /workspace/novnc-logs/isaac-gui.log
```

| Symptom | Cause / fix |
|---|---|
| Page loads, grey/empty desktop | Isaac still starting (1–2 min). Check `isaac-gui.log`. |
| Page won't load at all | 8080 not exposed as HTTP in the pod config, or websockify died — see `websockify.log`. |
| Isaac window never appears | Look for a Vulkan/GL error in `isaac-gui.log` — the GPU couldn't present to the virtual display. |
| Everything died after a restart | Re-run `bash novnc.sh` for Isaac or `SIMULATOR=gazebo bash novnc.sh` for Gazebo. |
| Gazebo reports an unsupported pairing | Use Ubuntu 22.04 + `ROS_DISTRO=humble` or Ubuntu 24.04 + `ROS_DISTRO=jazzy` inside the container. |
| Gazebo exits or its window stays blank | Check `gazebo-gui.log`; try `SIMULATOR=gazebo LIBGL_ALWAYS_SOFTWARE=1 bash novnc.sh`. |

⚠️ **Never kill the Isaac process the container itself started**
(`omni.isaac.sim.headless.*.kit`, usually PID ~54). On the RunPod image it is the
container's **main process** — killing it stops the whole container: SSH drops,
your work is gone, port mappings change. `novnc.sh` only ever touches the desktop
stack and the GUI instance it launched itself.

## Files

| File | Purpose |
|---|---|
| `bootstrap.sh` | **Start here.** Downloads the repo without git, then runs `novnc.sh`. |
| `novnc.sh` | Virtual display + VNC + noVNC + selected simulator GUI. Defaults to Isaac. |
| `gazebo.sh` | Gazebo compatibility, installation, ROS environment, launch and tracked session shutdown. |
| `stop.sh` | Stops the desktop cleanly (leaves the pod and its main process alive). |
| `install.sh` | Installs all dependencies via apt + pip. Called automatically; idempotent. |
| `requirements.txt` | Python dependencies (`websockify`). Also documents the apt-only system packages. |
| `TEMPLATE.md` | RunPod template settings + the description text to paste. |
| `POSTMORTEM.md` | Every approach tried, why each failed, why noVNC won. |
| `docs/knowledge-base/` | Project architecture, decisions and verification notes; Graphify/Obsidian locations. |

## Security

The noVNC endpoint has **no authentication by default** — anyone with the URL can
view and control the sim. Set `VNC_PASSWORD=...` if the pod URL might be shared,
and stop the pod when you're not using it.

## License

[MIT](LICENSE) — free to use, modify, and redistribute, including commercially.
Provided as-is, with no warranty.

Isaac Sim itself is NVIDIA's, under its own license. This repo only contains the
scripts that put its GUI in your browser.
