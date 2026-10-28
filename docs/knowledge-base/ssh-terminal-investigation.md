# SSH and browser-terminal investigation

Recorded 2026-10-28 from the user's supplied connection observations, read-only checks, and source inspection. The initial investigation preserved the original runtime. The user subsequently authorized targeted lifecycle and startup fixes before a new pod trial.

The user's SSH session authenticated, displayed a container root prompt in `/isaac-sim`, and then closed immediately. A local read-only connection check reproduced the closure before diagnostic commands could execute. A second attempt at the same endpoint was refused with `publickey` authentication failure; no further retries were made. A check of the supplied noVNC proxy route returned HTTP 404 at that time.

The user later clarified that the pod had been deleted. There is no live instance to inspect or repair. Authentication rejection and HTTP 404 after deletion cannot establish an application failure. The exact timing of deletion relative to the first session closure is not independently established. Historical System logs would be needed to correlate that closure with container events. Supplied GLFW warnings alone do not establish the fatal cause. No successful remote repair is claimed.

Before hardening, source restored from `cfdca8f` contained four relevant weaknesses (these line numbers refer to that original version):

- `novnc.sh:85` reads `isaac-gui.pid` and signals it without verifying process identity. A stale PID can refer to a different process; the supplied evidence does not show that this happened.
- `stop.sh:32-44` uses a PID and global GUI process-name patterns without display ownership checks. These selectors are broader than one launched GUI session.
- `stop.sh:49-56` splits pattern/description strings on `:` although an X display is `:1`. The first pass truncates the display from the Xvfb/x11vnc patterns and broadens their scope.
- `novnc.sh:173-176` expands `RUNPOD_POD_HOSTNAME` without an unset default under `set -u`. If both pod identifier variables are absent, startup can fail late while printing the URL. This does not establish the cause of the observed SSH closure.

The long-lived desktop and GUI processes use `setsid`. Source comments about preserving the container main process do not verify ownership of a deleted pod's processes. None of the source weaknesses is a confirmed cause of the reported connection behavior.

The latest user request overrides exact runtime preservation for targeted fixes. The implemented hardening replaces legacy-PID/global-name cleanup with verified owned-session tracking in `process_control.py`, removes X socket deletion, serializes stack changes, and guards absent RunPod variables. Startup reports early GUI failure and refuses unverified occupied displays. Installer output/cache handling and bootstrap scratch cleanup are also hardened. All 17 local unit methods pass; see validation for scope. No fresh pod result or confirmed explanation for the original SSH closure is claimed.

No new OS, Docker, or simulator downloads were performed; no keys were copied or credential values saved. Endpoint identifiers and key material are intentionally omitted.
