#!/usr/bin/env python3
"""Manage only this launcher's detached Linux sessions, using PID lifetime checks."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import time


OWNER = "runpod-isaac-novnc-v1"
COMPONENTS = ("isaac-gui", "websockify", "x11vnc", "fluxbox", "xvfb")


def process_info(pid):
    try:
        # comm may contain spaces/parentheses; fields after its final ')' start at state.
        fields = Path(f"/proc/{int(pid)}/stat").read_text().rsplit(")", 1)[1].split()
        return {"pid": int(pid), "state": fields[0], "ppid": int(fields[1]),
                "group": int(fields[2]), "session": int(fields[3]),
                "start_ticks": int(fields[19])}
    except (OSError, ValueError, IndexError):
        return None


def boot_id():
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def alive(info):
    return info is not None and info["state"] not in ("Z", "X")


def belongs(info, data):
    if (not alive(info) or info["session"] != data["pid"]
            or info["start_ticks"] < data["start_ticks"]):
        return False
    try:
        marker = f"NOVNC_SESSION_TOKEN={data['token']}".encode()
        return marker in Path(f"/proc/{info['pid']}/environ").read_bytes().split(b"\0")
    except OSError:
        return False


def protected_pids():
    protected = {1, os.getpid()}
    pid = os.getppid()
    while pid > 0 and pid not in protected:
        protected.add(pid)
        info = process_info(pid)
        pid = info["ppid"] if info else 0
    return protected


class Processes:
    def __init__(self, log_dir, display):
        if not re.fullmatch(r":\d+(?:\.\d+)?", display):
            raise ValueError("DISPLAY_NUM must look like :1 or :1.0")
        self.log_dir = Path(log_dir)
        self.display = display
        self.state_dir = self.log_dir / ".processes" / display.replace(":", "display-")
        self.children = {}

    def path(self, name):
        if name not in COMPONENTS:
            raise ValueError(f"Unknown component: {name}")
        return self.state_dir / f"{name}.json"

    def record(self, name):
        try:
            data = json.loads(self.path(name).read_text())
            if (data["owner"] != OWNER or data["display"] != self.display
                    or data["boot_id"] != boot_id() or not isinstance(data["pid"], int)
                    or data["pid"] <= 1 or not isinstance(data["start_ticks"], int)
                    or data["start_ticks"] <= 0 or not isinstance(data["token"], str)
                    or len(data["token"]) < 16):
                return None
            return data
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def matches(self, data):
        info = process_info(data["pid"])
        if alive(info):
            return (info["start_ticks"] == data["start_ticks"]
                    and info["group"] == data["pid"] and belongs(info, data))
        # A launcher can exit while its descendants remain. The inherited unique
        # marker identifies our surviving session without trusting a reused PID.
        return any(belongs(process_info(int(path.name)), data)
                   for path in Path("/proc").iterdir() if path.name.isdecimal())

    def start(self, name, command):
        if not command:
            raise ValueError("A command is required")
        old = self.record(name)
        if old and self.matches(old):
            raise RuntimeError(f"{name} is already running; stop the previous stack first")
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        token = secrets.token_hex(24)
        with (self.log_dir / f"{name}.log").open("wb") as output:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output,
                                     stderr=subprocess.STDOUT, start_new_session=True,
                                     env={**os.environ, "DISPLAY": self.display, "NOVNC_SESSION_TOKEN": token})
        info = process_info(child.pid)
        if not alive(info):
            child.poll()
            raise RuntimeError(f"{name} exited immediately; see {self.log_dir / (name + '.log')}")
        self.children[child.pid] = child
        data = {"owner": OWNER, "display": self.display, "boot_id": boot_id(),
                "pid": child.pid, "start_ticks": info["start_ticks"], "token": token}
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.state_dir, delete=False) as state:
                temporary = Path(state.name)
                json.dump(data, state)
            temporary.replace(self.path(name))
            # Retained for users inspecting logs. This file alone never authorizes a kill.
            (self.log_dir / f"{name}.pid").write_text(f"{child.pid}\n")
        except OSError:
            child.terminate()
            child.wait(timeout=5)
            raise
        print(f"[process] Started {name} on {self.display} (pid {child.pid}).")
        return child.pid

    def forget(self, name, data):
        self.path(name).unlink(missing_ok=True)
        legacy = self.log_dir / f"{name}.pid"
        try:
            if data and legacy.read_text().strip() == str(data["pid"]):
                legacy.unlink()
        except OSError:
            pass

    def stop(self, name, timeout=5):
        data = self.record(name)
        if not data or not self.matches(data):
            if self.path(name).exists() or (self.log_dir / f"{name}.pid").exists():
                print(f"[process] Ignoring stale or unverified {name} PID; no process was signalled.")
            self.forget(name, data)
            return
        protected = protected_pids()
        if data["pid"] in protected:
            print(f"[process] Refusing to stop protected {name} process.")
            return

        # Record each member's lifetime before signalling. A reused PID, another
        # session, PID 1, and the calling shell's ancestors are never targets.
        members = {}

        def refresh():
            for path in Path("/proc").iterdir():
                if path.name.isdecimal():
                    info = process_info(int(path.name))
                    if belongs(info, data):
                        members[info["pid"]] = info["start_ticks"]

        def current():
            found = []
            for pid, ticks in members.items():
                info = process_info(pid)
                if (alive(info) and info["start_ticks"] == ticks
                        and info["session"] == data["pid"]):
                    found.append(pid)
            return found

        def send(pids, sig):
            for pid in pids:
                info = process_info(pid)
                if (pid not in protected and alive(info) and info["session"] == data["pid"]
                        and info["start_ticks"] == members[pid]):
                    try:
                        os.kill(pid, sig)
                    except ProcessLookupError:
                        pass

        refresh()
        if protected.intersection(members):
            print(f"[process] Preserving {name}: its session contains the calling terminal.")
            return
        print(f"[process] Stopping verified {name} session {data['pid']}...")
        send(current(), signal.SIGTERM)
        deadline = time.monotonic() + timeout
        while current() and time.monotonic() < deadline:
            # A verified surviving member anchors this still-owned session.
            refresh()
            time.sleep(0.05)
        send(current(), signal.SIGKILL)
        if data["pid"] in self.children:
            self.children.pop(data["pid"]).wait(timeout=5)
        self.forget(name, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", required=True)
    parser.add_argument("--display", default=":1")
    sub = parser.add_subparsers(dest="action", required=True)
    start = sub.add_parser("start")
    start.add_argument("name", choices=COMPONENTS)
    start.add_argument("command", nargs=argparse.REMAINDER)
    stop = sub.add_parser("stop")
    stop.add_argument("name", nargs="?", choices=COMPONENTS)
    stop.add_argument("--timeout", type=float, default=5)
    status = sub.add_parser("status")
    status.add_argument("name", choices=COMPONENTS)
    args = parser.parse_args()
    processes = Processes(args.log_dir, args.display)
    if args.action == "start":
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        processes.start(args.name, command)
    elif args.action == "stop":
        for name in ([args.name] if args.name else COMPONENTS):
            processes.stop(name, args.timeout)
    else:
        data = processes.record(args.name)
        return 0 if data and processes.matches(data) else 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(f"[process] ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
