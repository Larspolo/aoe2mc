"""The wheel installs one top-level package, not the generic names units, gui, data ... (#3056)."""
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def wheel(tmp_path_factory):
    out = tmp_path_factory.mktemp("wheel")
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "-q", "-w", str(out),
                    str(ROOT)], check=True, capture_output=True)
    return next(out.glob("aoe2mc-*.whl"))


@pytest.mark.slow
def test_one_top_level_folder(wheel):
    tops = {n.split("/")[0] for n in zipfile.ZipFile(wheel).namelist()}
    assert {t for t in tops if not t.endswith(".dist-info")} == {"aoe2mc_app"}


@pytest.mark.slow
def test_foreign_units_package_does_not_break_the_command(wheel, tmp_path):
    zipfile.ZipFile(wheel).extractall(tmp_path)
    (tmp_path / "units").mkdir()
    (tmp_path / "units" / "__init__.py").write_text("")
    code = "import sys; from aoe2mc_app.aoe2mc import main; sys.argv = ['aoe2mc', '--help']; main()"
    r = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": str(tmp_path)})
    assert r.returncode == 0, r.stderr
    assert "usage" in r.stdout


@pytest.mark.slow
def test_installed_command_converts(wheel, tmp_path):
    zipfile.ZipFile(wheel).extractall(tmp_path)
    (tmp_path / "units").mkdir()
    (tmp_path / "units" / "__init__.py").write_text("")
    code = "import sys; from aoe2mc_app.aoe2mc import main; sys.argv[0] = 'aoe2mc'; main()"
    r = subprocess.run([sys.executable, "-c", code, str(ROOT / "samples" / "test_village.aoe2scenario"),
                        str(tmp_path / "World")], cwd=tmp_path, capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": str(tmp_path)})
    assert r.returncode == 0, r.stderr[-2000:]
    assert (tmp_path / "World" / "level.dat").exists()
