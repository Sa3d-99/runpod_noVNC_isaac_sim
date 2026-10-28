"""Compatibility and process isolation checks; no apt or graphics required."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CompatibilityTests(unittest.TestCase):
    def select(self, os_id, version, distro=""):
        with tempfile.TemporaryDirectory() as directory:
            release = Path(directory) / "os-release"
            release.write_text(f'ID={os_id}\nVERSION_ID="{version}"\n')
            return subprocess.run(
                ["bash", "-euc", 'source "$1"; gazebo_select_platform "$2"; '
                 'printf "%s %s %s" "$ROS_DISTRO" "$GAZEBO_RELEASE" "$GAZEBO_CODENAME"',
                 "test", str(ROOT / "gazebo.sh"), str(release)],
                env={**os.environ, "ROS_DISTRO": distro},
                capture_output=True, text=True, check=False,
            )

    def test_supported_platforms_and_automatic_selection(self):
        for version, distro, release, codename in (
            ("22.04", "humble", "Fortress", "jammy"),
            ("24.04", "jazzy", "Harmonic", "noble"),
        ):
            for configured in ("", distro):
                with self.subTest(version=version, configured=configured):
                    result = self.select("ubuntu", version, configured)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, f"{distro} {release} {codename}")

    def test_mismatches_and_other_ros_versions_are_rejected(self):
        for version, distro in (("22.04", "jazzy"), ("24.04", "humble"),
                                ("22.04", "iron"), ("24.04", "rolling")):
            with self.subTest(version=version, distro=distro):
                result = self.select("ubuntu", version, distro)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unsupported", result.stderr)

    def test_other_operating_systems_are_rejected(self):
        for os_id, version in (("ubuntu", "20.04"), ("ubuntu", "26.04"),
                               ("debian", "12"), ("linuxmint", "22.04")):
            with self.subTest(os_id=os_id, version=version):
                result = self.select(os_id, version)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("only Ubuntu", result.stderr)

    def test_invalid_selection_fails_before_install_or_desktop_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_bin = Path(directory) / "bin"
            fake_bin.mkdir()
            marker = Path(directory) / "unexpected-command"
            for command in ("apt-get", "pkill", "Xvfb"):
                stub = fake_bin / command
                stub.write_text('#!/bin/sh\ntouch "$UNEXPECTED_COMMAND"\nexit 91\n')
                stub.chmod(0o755)
            env = {**os.environ, "SIMULATOR": "unsupported", "LOG_DIR": directory,
                   "PATH": f"{fake_bin}:{os.environ['PATH']}",
                   "UNEXPECTED_COMMAND": str(marker)}
            for script in ("install.sh", "novnc.sh"):
                with self.subTest(script=script):
                    result = subprocess.run(["bash", str(ROOT / script)], env=env,
                                            capture_output=True, text=True, check=False)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("SIMULATOR must be", result.stderr)
                    self.assertFalse(marker.exists())


class ShutdownTests(unittest.TestCase):
    def test_stops_recorded_session_and_leaves_other_processes_running(self):
        with tempfile.TemporaryDirectory() as directory:
            # Parent reaps its child on SIGINT, matching ROS launch's shutdown.
            leader = subprocess.Popen(
                [sys.executable, "-c",
                 "import subprocess,signal,sys,time; "
                 "child=subprocess.Popen(['sleep','300']); "
                 "signal.signal(signal.SIGINT,lambda *_:(child.wait(),sys.exit(0))); "
                 "print('ready',flush=True); time.sleep(300)"],
                start_new_session=True, stdout=subprocess.PIPE, text=True,
            )
            unrelated = subprocess.Popen(["sleep", "300"], start_new_session=True)
            try:
                self.assertEqual(leader.stdout.readline().strip(), "ready")
                pid_file = Path(directory) / "gazebo-gui.pid"
                pid_file.write_text(str(leader.pid))
                result = subprocess.run(
                    ["bash", str(ROOT / "gazebo.sh"), "stop"],
                    env={**os.environ, "LOG_DIR": directory},
                    capture_output=True, text=True, timeout=20, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                leader.wait(timeout=3)
                self.assertIsNone(unrelated.poll())
                self.assertFalse(pid_file.exists())
            finally:
                if leader.poll() is None:
                    os.killpg(leader.pid, 9)
                leader.wait()
                leader.stdout.close()
                unrelated.terminate()
                unrelated.wait()

    def test_stop_is_safe_with_missing_stale_or_invalid_pid(self):
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "gazebo-gui.pid"
            for value in (None, "not-a-pid", "0", "1", "999999999"):
                with self.subTest(value=value):
                    if value is not None:
                        pid_file.write_text(value)
                    subprocess.run(
                        ["bash", str(ROOT / "gazebo.sh"), "stop"],
                        env={**os.environ, "LOG_DIR": directory},
                        capture_output=True, text=True, timeout=3, check=True,
                    )
                    self.assertFalse(pid_file.exists())


if __name__ == "__main__":
    unittest.main()
