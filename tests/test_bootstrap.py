import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from test_startup import ROOT, executable


class BootstrapTests(unittest.TestCase):
    def test_download_progress_and_temporary_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "bin").mkdir()
            source = directory / "runpod_noVNC_isaac_sim-main"
            source.mkdir()
            executable(source / "novnc.sh", '#!/bin/sh\necho LAUNCHER_STARTED\n')
            archive = directory / "archive.tar.gz"
            with tarfile.open(archive, "w:gz") as output:
                output.add(source, arcname=source.name)
            executable(directory / "bin/curl", '''
                #!/usr/bin/env python3
                import os,pathlib,shutil,sys
                args=sys.argv[1:]
                pathlib.Path(os.environ['URL_MARKER']).write_text(next(a for a in args if a.startswith('https://')))
                print('Download progress: 50%',file=sys.stderr)
                shutil.copyfile(os.environ['ARCHIVE'],args[args.index('-o')+1])
            ''')
            env = dict(os.environ)
            for key in ("REPO", "BRANCH"):
                env.pop(key, None)
            env.update({"PATH": f"{directory / 'bin'}:{env['PATH']}", "TMPDIR": str(directory),
                        "DEST": str(directory / "installed"), "ARCHIVE": str(archive),
                        "URL_MARKER": str(directory / "url")})
            result = subprocess.run(["bash", str(ROOT / "bootstrap.sh")], env=env,
                                    capture_output=True, text=True, timeout=10, check=True)
            self.assertEqual((directory / "url").read_text(),
                             "https://codeload.github.com/Sa3d-99/runpod_noVNC_isaac_sim/tar.gz/refs/heads/main")
            self.assertIn("Download progress: 50%", result.stderr)
            self.assertIn("LAUNCHER_STARTED", result.stdout)
            self.assertFalse(list(directory.glob("tmp.*")))


if __name__ == "__main__":
    unittest.main()
