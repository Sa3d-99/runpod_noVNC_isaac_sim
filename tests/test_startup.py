"""Run the actual shell launch/stop scripts against isolated fake display services."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import textwrap
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]


def executable(path, content):
    path.write_text(textwrap.dedent(content).lstrip())
    path.chmod(0o755)


class StartupTests(unittest.TestCase):
    def prepare(self, directory):
        (directory / "bin").mkdir()
        (directory / "fake-isaac").mkdir()
        for name in ("novnc.sh", "stop.sh", "process_control.py"):
            shutil.copy2(ROOT / name, directory / name)
        executable(directory / "install.sh", "#!/bin/sh\nexit 0\n")
        service = '''
            #!/usr/bin/env python3
            import os,pathlib,signal,socket,sys,time
            name=pathlib.Path(sys.argv[0]).name
            ready=pathlib.Path(os.environ['DISPLAY_MARKER'])
            def stop(*_):
                if name=='Xvfb': ready.unlink(missing_ok=True)
                raise SystemExit(0)
            signal.signal(signal.SIGTERM,stop)
            if name=='Xvfb': ready.touch()
            if name=='isaac-sim.sh':
                pathlib.Path(os.environ['GUI_MARKER']).write_text(os.environ['DISPLAY']+'|'+' '.join(sys.argv[1:]))
            if name in ('x11vnc','websockify'):
                args=sys.argv[1:]
                port=int(args[args.index('-rfbport')+1] if name=='x11vnc' else args[1])
                sock=socket.socket(); sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                sock.bind(('127.0.0.1',port)); sock.listen()
            time.sleep(300)
        '''
        for name in ("Xvfb", "fluxbox", "x11vnc", "websockify"):
            executable(directory / "bin" / name, service)
        executable(directory / "fake-isaac/isaac-sim.sh", service)
        executable(directory / "bin/xdpyinfo", '#!/bin/sh\ntest -f "$DISPLAY_MARKER"\n')
        executable(directory / "bin/pkill", '#!/bin/sh\necho unsafe-kill >> "$UNSAFE_MARKER"\nexit 1\n')
        sockets = [socket.socket(), socket.socket()]
        try:
            for sock in sockets:
                sock.bind(("127.0.0.1", 0))
            ports = [sock.getsockname()[1] for sock in sockets]
        finally:
            for sock in sockets:
                sock.close()
        env = dict(os.environ)
        for key in ("RUNPOD_POD_ID", "RUNPOD_POD_HOSTNAME", "VNC_PASSWORD"):
            env.pop(key, None)
        env.update({"PATH": f"{directory / 'bin'}:{env['PATH']}", "DISPLAY_NUM": ":19997",
                    "LOG_DIR": str(directory / "logs"), "VNC_PORT": str(ports[0]),
                    "WEB_PORT": str(ports[1]), "ISAAC_ROOT": str(directory / "fake-isaac"),
                    "DISPLAY_MARKER": str(directory / "display-ready"),
                    "GUI_MARKER": str(directory / "gui-started"),
                    "UNSAFE_MARKER": str(directory / "unsafe-kill")})
        return env

    def run_script(self, directory, name, env, check=True):
        return subprocess.run(["bash", str(directory / name)], env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              timeout=25, check=check)

    def test_full_gui_and_missing_hostname_stop_only_managed_services(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            env = self.prepare(directory)
            unrelated = subprocess.Popen(["bash", "-c", "exec -a omni.isaac.sim.kit sleep 300"],
                                         start_new_session=True)
            (directory / "logs").mkdir()
            (directory / "logs/isaac-gui.pid").write_text(str(unrelated.pid))
            try:
                result = self.run_script(directory, "novnc.sh", {**env, "NO_ISAAC": "0"})
                self.assertIn("pod id is not in", result.stdout)
                self.assertIsNone(unrelated.poll())
                deadline = time.monotonic() + 3
                while not (directory / "gui-started").exists():
                    self.assertLess(time.monotonic(), deadline,
                                    (directory / "logs/isaac-gui.log").read_text())
                    time.sleep(0.01)
                self.assertEqual((directory / "gui-started").read_text(), ":19997|--allow-root")
                self.run_script(directory, "stop.sh", env)
                self.assertIsNone(unrelated.poll())
                self.assertFalse((directory / "display-ready").exists())
                self.assertFalse(list((directory / "logs/.processes").glob("**/*.json")))
                self.assertFalse((directory / "unsafe-kill").exists())
            finally:
                self.run_script(directory, "stop.sh", env, check=False)
                unrelated.terminate()
                unrelated.wait()

    def test_desktop_only_and_restart_reuse_safe_tracking(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            env = {**self.prepare(directory), "NO_ISAAC": "1", "RUNPOD_POD_ID": "test-pod"}
            try:
                for _ in range(2):
                    result = self.run_script(directory, "novnc.sh", env)
                    self.assertIn("skipping Isaac launch", result.stdout)
                    self.assertIn("test-pod-", result.stdout)
                    self.assertFalse((directory / "gui-started").exists())
                self.run_script(directory, "stop.sh", env)
                self.assertFalse((directory / "display-ready").exists())
                self.assertFalse((directory / "unsafe-kill").exists())
            finally:
                self.run_script(directory, "stop.sh", env, check=False)

    def test_existing_unverified_display_is_left_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            env = self.prepare(directory)
            (directory / "display-ready").touch()
            result = self.run_script(directory, "novnc.sh", env, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unverified server", result.stderr)
            self.assertTrue((directory / "display-ready").exists())
            self.assertFalse((directory / "unsafe-kill").exists())
            self.assertFalse(list((directory / "logs/.processes").glob("**/*.json")))

    def test_early_gui_failure_prints_its_log(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            env = {**self.prepare(directory), "NO_ISAAC": "0"}
            executable(directory / "fake-isaac/isaac-sim.sh",
                       "#!/bin/sh\necho GUI_FAILURE_FOR_TEST\nexit 23\n")
            try:
                result = self.run_script(directory, "novnc.sh", env, check=False)
                self.assertIn("GUI_FAILURE_FOR_TEST", result.stdout + result.stderr)
                self.assertNotIn("GUI takes 1-2 min", result.stdout)
            finally:
                self.run_script(directory, "stop.sh", env, check=False)


if __name__ == "__main__":
    unittest.main()
