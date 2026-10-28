"""Check visible installation output and cache isolation without host package changes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from test_startup import ROOT, executable

class InstallProgressTests(unittest.TestCase):
    def test_pip_failure_is_visible_in_terminal_and_install_log(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "bin").mkdir()
            for name in ("install.sh", "install-utils.sh"):
                shutil.copy2(ROOT / name, directory / name)
            (directory / "requirements.txt").write_text("websockify>=0.11.0\n")
            for command in ("git", "Xvfb", "x11vnc", "fluxbox", "websockify", "xdpyinfo", "apt-get"):
                executable(directory / "bin" / command, "#!/bin/sh\nexit 0\n")
            executable(directory / "bin/id", "#!/bin/sh\necho 0\n")
            executable(directory / "bin/python3", '''
                #!/bin/sh
                if [ "$1" = -c ]; then exit 1; fi
                if [ "$3" = --version ]; then exit 0; fi
                echo 'E: simulated Python package download failed' >&2
                exit 100
            ''')
            env = {**os.environ, "PATH": f"{directory / 'bin'}:{os.environ['PATH']}",
                   "TMPDIR": str(directory), "LOG_DIR": str(directory / "logs")}
            result = subprocess.run(["bash", str(directory / "install.sh")], env=env,
                                    capture_output=True, text=True, timeout=10, check=False)
            self.assertEqual(result.returncode, 100, result.stdout + result.stderr)
            for output in (result.stdout, (directory / "logs/install.log").read_text()):
                self.assertIn("simulated Python package download failed", output)
                self.assertIn("Installation stopped (exit 100)", output)
                self.assertNotIn("[install] Ready.", output)

    def prepare(self, directory):
        (directory / "bin").mkdir()
        default_cache = directory / "default-cache"
        (default_cache / "partial").mkdir(parents=True)
        executable(directory / "bin/apt-get", '''
            #!/usr/bin/env python3
            import json, os, pathlib, shutil, sys
            args = sys.argv[1:]
            cache = next(a.split('=', 1)[1] for a in args if a.startswith('Dir::Cache::archives='))
            cache = pathlib.Path(cache)
            partial = cache / 'partial/package.deb'
            partial.write_text('package content')
            print('Get:1 package.deb 50% [1 MB]', flush=True)
            print('Package tool stderr is visible', file=sys.stderr, flush=True)
            # Reproduce a default-cache cleaner running during a download.
            shutil.rmtree(os.environ['DEFAULT_CACHE'])
            partial.rename(cache / 'package.deb')
            pathlib.Path(os.environ['APT_RECORD']).write_text(json.dumps({'args': args, 'cache': str(cache)}))
            if os.environ.get('APT_FAIL') == '1':
                print('E: simulated package download failure', file=sys.stderr)
                sys.exit(100)
            print('Setting up package...', flush=True)
        ''')
        return {**os.environ, "PATH": f"{directory / 'bin'}:{os.environ['PATH']}",
                "TMPDIR": str(directory), "LOG_DIR": str(directory / "logs"),
                "DEFAULT_CACHE": str(default_cache), "APT_RECORD": str(directory / "apt.json")}

    def run_install(self, env):
        return subprocess.run(
            ["bash", "-euc", 'source "$1"; SUDO=""; install_prepare_apt; '
             'install_apt install -y demo-package; echo INSTALL_SUCCEEDED',
             "test", str(ROOT / "install-utils.sh")], env=env,
            capture_output=True, text=True, timeout=10, check=False,
        )

    def test_progress_visible_and_private_cache_survives_default_cache_cleaner(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            env = self.prepare(directory)
            result = self.run_install(env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("50%", result.stdout)
            self.assertIn("Setting up package", result.stdout)
            self.assertIn("stderr is visible", result.stderr)
            record = json.loads((directory / "apt.json").read_text())
            self.assertNotEqual(record["cache"], env["DEFAULT_CACHE"])
            self.assertIn("quiet=0", record["args"])
            self.assertIn("Acquire::Retries=3", record["args"])
            self.assertIn("DPkg::Lock::Timeout=300", record["args"])
            self.assertNotIn("--fix-missing", record["args"])
            self.assertFalse(Path(record["cache"]).exists(), "Private downloads must be cleaned after exit")

    def test_failure_is_visible_and_does_not_report_success(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            env = {**self.prepare(directory), "APT_FAIL": "1"}
            result = self.run_install(env)
            self.assertEqual(result.returncode, 100, result.stdout + result.stderr)
            self.assertIn("simulated package download failure", result.stderr)
            self.assertIn("Installation stopped (exit 100)", result.stdout)
            self.assertNotIn("INSTALL_SUCCEEDED", result.stdout)
            record = json.loads((directory / "apt.json").read_text())
            self.assertFalse(Path(record["cache"]).exists())

    def test_another_installer_waits_for_the_existing_install(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            env = {**os.environ, "TMPDIR": str(directory), "LOG_DIR": str(directory)}
            holder = subprocess.Popen(
                ["bash", "-euc", 'source "$1"; install_prepare_apt; '
                 'echo first_started >> "$2/events"; touch "$2/ready"; '
                 'sleep 0.5; echo first_done >> "$2/events"',
                 "test", str(ROOT / "install-utils.sh"), str(directory)],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            )
            try:
                deadline = time.monotonic() + 5
                while not (directory / "ready").exists():
                    self.assertIsNone(holder.poll())
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.01)
                result = subprocess.run(
                    ["bash", "-euc", 'source "$1"; install_prepare_apt; echo second_started >> "$2/events"',
                     "test", str(ROOT / "install-utils.sh"), str(directory)],
                    env=env, capture_output=True, text=True, timeout=5, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((directory / "events").read_text().splitlines(),
                                 ["first_started", "first_done", "second_started"])
                holder.wait(timeout=5)
                self.assertEqual(holder.returncode, 0)
            finally:
                if holder.poll() is None:
                    holder.terminate()
                holder.wait()
                holder.stderr.close()
