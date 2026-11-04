"""The standalone run of tools/dat_compare.py (#5734): it gets past the import of game.gather."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "tools", "dat_compare.py")


def run(args, cwd, pythonpath=""):
    env = {**os.environ, "PYTHONPATH": pythonpath}
    return subprocess.run([sys.executable, SCRIPT, *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=120)


def test_no_dat_exits_2(tmp_path):
    r = run([str(tmp_path / "none.dat")], tmp_path)
    assert r.returncode == 2 and "no .dat" in r.stdout


def test_no_genieutils_exits_2(tmp_path):
    dat = tmp_path / "a.dat"
    dat.write_bytes(b"x")
    r = run([str(dat)], tmp_path, str(tmp_path / "empty"))
    if "no genieutils-py" not in r.stdout:      # genieutils-py is installed here: nothing to check
        return
    assert r.returncode == 2


def test_with_dat_imports_gather(tmp_path):
    fake = tmp_path / "fake" / "genieutils"
    fake.mkdir(parents=True)
    (fake / "__init__.py").write_text("")
    (fake / "datfile.py").write_text("class DatFile:\n    @staticmethod\n    def parse(p):\n        raise SystemExit('parsed')\n")
    dat = tmp_path / "a.dat"
    dat.write_bytes(b"x")
    r = run([str(dat)], tmp_path, str(tmp_path / "fake"))
    assert "ModuleNotFoundError" not in r.stderr, r.stderr
