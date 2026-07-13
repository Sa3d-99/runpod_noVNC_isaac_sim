# Isaac Sim on RunPod — browser access that actually works (noVNC)

Run NVIDIA Isaac Sim on a RunPod pod and use its **full GUI in your browser**.
Works on **all Isaac Sim versions** (4.0 → 5.x). No UDP, no WebRTC, no ICE, no
TURN, no Direct-TCP ports — one HTTP port and you're done.

One script. One command. That's the whole repo.

## Quick start — one command, nothing pre-installed

A fresh RunPod Isaac pod has **no git**, and often runs as the unprivileged
`isaac-sim` user. So don't clone — bootstrap:

```bash
curl -fsSL https://raw.githubusercontent.com/Sa3d-99/runpod_noVNC_isaac_sim/main/bootstrap.sh | bash
```

That downloads the repo (no git needed), installs every dependency (using `sudo`
automatically if you're not root), starts the desktop, launches Isaac Sim, and
**prints your real URL** — no placeholder to fill in.

Then open the printed link. It looks like:

```
https://<your-pod-id>-8080.proxy.runpod.net/vnc.html?autoconnect=1&resize=remote
```

(also saved to `/workspace/novnc-logs/novnc_url.txt` — `cat` it any time)

Isaac Sim's GUI appears on the desktop after 1–2 minutes. Load your scene with
**File → Open**. Mouse and keyboard work normally.

**Requirement:** port **8080** exposed as an **HTTP** port (default on the Isaac
images). Nothing else — no Direct TCP ports, no port mappings to copy after a
restart.

### If you already have the repo

```bash
cd /workspace/runpod_noVNC_isaac_sim && bash novnc.sh
```

## How it works

```
Isaac Sim GUI  →  renders into a virtual X screen (Xvfb, on the GPU)
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

## Automatic on pod boot

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
```

Example: `RES=2560x1440 VNC_PASSWORD=hunter2 bash novnc.sh`

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
| Everything died after a restart | Re-run `bash novnc.sh` — it's idempotent and cleans up its own previous run. |

⚠️ **Never kill the Isaac process the container itself started**
(`omni.isaac.sim.headless.*.kit`, usually PID ~54). On the RunPod image it is the
container's **main process** — killing it stops the whole container: SSH drops,
your work is gone, port mappings change. `novnc.sh` only ever touches the desktop
stack and the GUI instance it launched itself.

## Files

| File | Purpose |
|---|---|
| `bootstrap.sh` | **Start here.** Downloads the repo without git, then runs `novnc.sh`. |
| `novnc.sh` | The method. Virtual display + VNC + noVNC + Isaac GUI. |
| `install.sh` | Installs all dependencies via apt + pip. Called automatically; idempotent. |
| `requirements.txt` | Python dependencies (`websockify`). Also documents the apt-only system packages. |
| `POSTMORTEM.md` | Every approach tried, why each failed, why noVNC won. |

## Security

The noVNC endpoint has **no authentication by default** — anyone with the URL can
view and control the sim. Set `VNC_PASSWORD=...` if the pod URL might be shared,
and stop the pod when you're not using it.
