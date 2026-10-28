"""Use disposable processes to verify cleanup never trusts reused or legacy PIDs."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from process_control import OWNER, Processes, boot_id, process_info


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manager = Processes(self.root, ":19999")
        self.extra = []

    def tearDown(self):
        for child in list(self.manager.children.values()) + self.extra:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            child.wait()
        self.temp.cleanup()

    def unrelated(self):
        child = subprocess.Popen(["bash", "-c", "exec -a omni.isaac.sim.kit sleep 300"],
                                 start_new_session=True,
                                 env={**os.environ, "NOVNC_SESSION_TOKEN": "unrelated-test-token"})
        self.extra.append(child)
        return child

    def write_record(self, data):
        path = self.manager.path("isaac-gui")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def test_legacy_pid_cannot_kill_unrelated_isaac_process(self):
        child = self.unrelated()
        (self.root / "isaac-gui.pid").write_text(str(child.pid))
        self.manager.stop("isaac-gui", timeout=0.1)
        self.assertIsNone(child.poll())

    def test_reused_pid_start_time_mismatch_is_preserved(self):
        child = self.unrelated()
        info = process_info(child.pid)
        self.write_record({"owner": OWNER, "display": ":19999", "boot_id": boot_id(),
                           "pid": child.pid, "start_ticks": info["start_ticks"] - 1,
                           "token": "unrelated-test-token"})
        self.manager.stop("isaac-gui", timeout=0.1)
        self.assertIsNone(child.poll())

    def test_other_boot_or_display_and_malformed_state_are_preserved(self):
        child = self.unrelated()
        base = {"owner": OWNER, "display": ":19999", "boot_id": boot_id(),
                "pid": child.pid, "start_ticks": process_info(child.pid)["start_ticks"],
                "token": "unrelated-test-token"}
        for update in ({"boot_id": "old-boot"}, {"display": ":2"},
                       {"owner": "someone-else"}, {"start_ticks": "invalid"}):
            with self.subTest(update=update):
                self.write_record({**base, **update})
                self.manager.stop("isaac-gui", timeout=0.1)
                self.assertIsNone(child.poll())
        self.manager.path("isaac-gui").write_text("invalid-json")
        self.manager.stop("isaac-gui", timeout=0.1)
        self.assertIsNone(child.poll())

    def test_pid_one_is_never_signalled(self):
        self.write_record({"owner": OWNER, "display": ":19999", "boot_id": boot_id(),
                           "pid": 1, "start_ticks": process_info(1)["start_ticks"],
                           "token": "pid-one-test-token"})
        with patch("process_control.os.kill") as kill:
            self.manager.stop("isaac-gui", timeout=0.1)
            kill.assert_not_called()

    def test_current_shell_ancestors_are_never_signalled(self):
        pid = self.manager.start("isaac-gui", ["sleep", "300"])
        with patch("process_control.protected_pids", return_value={1, pid}), patch("process_control.os.kill") as kill:
            self.manager.stop("isaac-gui", timeout=0.1)
            kill.assert_not_called()
        self.assertIsNone(self.manager.children[pid].poll())

    def test_verified_session_stops_children_and_preserves_unrelated_process(self):
        unrelated = self.unrelated()
        child_pid = self.root / "child.pid"
        program = ("import subprocess,time,pathlib; "
                   "child=subprocess.Popen(['sleep','300']); "
                   f"pathlib.Path({str(child_pid)!r}).write_text(str(child.pid)); time.sleep(300)")
        pid = self.manager.start("isaac-gui", [sys.executable, "-c", program])
        deadline = time.monotonic() + 3
        while not child_pid.exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        descendant = int(child_pid.read_text())
        self.manager.stop("isaac-gui", timeout=0.2)
        self.assertIsNone(unrelated.poll())
        for target in (pid, descendant):
            info = process_info(target)
            self.assertTrue(info is None or info["state"] in ("Z", "X"), info)
        self.assertFalse(self.manager.path("isaac-gui").exists())

    def test_sigkill_fallback_for_our_stubborn_process(self):
        ready = self.root / "ready"
        code = ("import pathlib,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                f"pathlib.Path({str(ready)!r}).touch(); time.sleep(300)")
        pid = self.manager.start("fluxbox", [sys.executable, "-c", code])
        deadline = time.monotonic() + 3
        while not ready.exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        self.manager.stop("fluxbox", timeout=0.1)
        self.assertIsNone(process_info(pid))

    def test_orphaned_child_is_still_owned_after_launcher_exits(self):
        marker = self.root / "orphan.pid"
        code = ("import subprocess,pathlib,time; child=subprocess.Popen(['sleep','300']); "
                f"pathlib.Path({str(marker)!r}).write_text(str(child.pid)); time.sleep(0.2)")
        leader = self.manager.start("isaac-gui", [sys.executable, "-c", code])
        self.manager.children[leader].wait(timeout=3)
        orphan = int(marker.read_text())
        try:
            self.manager.stop("isaac-gui", timeout=0.2)
            info = process_info(orphan)
            self.assertTrue(info is None or info["state"] in ("Z", "X"), info)
        finally:
            info = process_info(orphan)
            if info is not None and info["state"] not in ("Z", "X"):
                os.kill(orphan, signal.SIGKILL)


if __name__ == "__main__":
    unittest.main()
