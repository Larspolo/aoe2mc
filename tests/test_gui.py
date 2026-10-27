"""gui.py: the converter window (#1540). The pure functions run without a display; the window test opens the window
under xvfb-run and skips without tkinter or a display."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import gui

ROOT = Path(__file__).resolve().parent.parent


def test_argv_has_each_field():
    o = {"input": "a.aoe2scenario", "output": "/saves/a"}
    assert gui.argv(o) == ["a.aoe2scenario", "/saves/a"]
    assert gui.argv(o | {"name": "My map"})[2:] == ["--name", "My map"]
    assert gui.argv(o | {"tile_size": "5"})[2:] == ["--tile-size", "5"]
    assert gui.argv(o | {"level_height": " 2 "})[2:] == ["--level-height", "2"]
    assert gui.argv(o | {"architecture": "eastern"})[2:] == ["--architecture", "eastern"]
    assert gui.argv(o | {"seed": "7"})[2:] == ["--seed", "7"]
    assert gui.argv(o | {"preview": True})[2:] == ["--preview"]
    assert gui.argv(o | {"no_units": True})[2:] == ["--no-units"]
    assert gui.argv(o | {"more": "--border void --spawn '3,4'"})[2:] == ["--border", "void", "--spawn", "3,4"]
    assert gui.argv(o | {"name": "", "architecture": "", "preview": False, "more": ""}) == gui.argv(o)


def test_at_only_for_a_recorded_game():
    assert gui.argv({"input": "a.aoe2scenario", "output": "w", "at": "10:00"}) == ["a.aoe2scenario", "w"]
    assert gui.argv({"input": "g.AOE2RECORD", "output": "w", "at": "10:00"})[2:] == ["--at", "10:00"]
    assert gui.argv({"input": "g.mgz", "output": "w", "at": "5:30"})[2:] == ["--at", "5:30"]


def test_saves_folder_of_each_system():
    assert gui.saves_folder("Windows", {"APPDATA": "C:/Users/a/AppData/Roaming"}) == \
        Path("C:/Users/a/AppData/Roaming") / ".minecraft" / "saves"
    assert gui.saves_folder("Darwin", {"HOME": "/Users/a"}) == Path("/Users/a/Library/Application Support/minecraft/saves")
    assert gui.saves_folder("Linux", {"HOME": "/home/a"}) == Path("/home/a/.minecraft/saves")


def test_world_name_does_not_clash(tmp_path):
    assert gui.world_name("/x/My Map.aoe2scenario", tmp_path) == "My Map"
    (tmp_path / "My Map").mkdir()
    (tmp_path / "My Map 2").mkdir()
    assert gui.world_name("/x/My Map.aoe2scenario", tmp_path) == "My Map 3"


def test_import_needs_no_tkinter():
    assert "tkinter" not in subprocess.run([sys.executable, "-c", "import sys, gui; print(sorted(sys.modules))"],
                                           cwd=ROOT, capture_output=True, text=True, check=True).stdout


def test_convert_writes_a_world(tmp_path):
    out = []
    o = {"input": str(ROOT / "samples" / "test_village.aoe2scenario"), "output": str(tmp_path / "W"), "no_units": True}
    assert gui.convert(gui.argv(o), out.append) is None
    assert (tmp_path / "W" / "level.dat").is_file() and "".join(out)


def test_convert_returns_the_error_of_a_wrong_option(tmp_path):
    out = []
    assert gui.convert(["a.aoe2scenario", str(tmp_path / "W"), "--tile-size", "99"], out.append)
    assert "--tile-size" in "".join(out)


def test_the_window_opens_and_closes():
    if subprocess.run([sys.executable, "-c", "import tkinter"], capture_output=True).returncode:
        pytest.skip("no tkinter")
    cmd = [sys.executable, "-c", "import gui; w = gui.window(); w.update(); w.destroy(); print('ok')"]
    if not os.environ.get("DISPLAY"):
        if not shutil.which("xvfb-run"):
            pytest.skip("no display and no xvfb-run")
        cmd = ["xvfb-run", "-a"] + cmd
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and r.stdout.strip() == "ok", r.stderr
