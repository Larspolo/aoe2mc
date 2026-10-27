# PyInstaller spec of the app bundle (#1541): one folder "aoe2mc" with the window (aoe2mc-gui, gui.run of #1540) and
# the command line (aoe2mc, aoe2mc.main). Build: python3 -m PyInstaller packaging/aoe2mc.spec (docs/packaging.md).
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.dirname(SPECPATH)
# aoe2mc.py reads tools/mcdata/26.3.json next to itself; the parsers read their own data files (a missing file gives
# an error only at run time, so the workflow converts a scenario and a record)
DATAS = ([(os.path.join(ROOT, "tools", "mcdata", "26.3.json"), os.path.join("tools", "mcdata"))]
         + collect_data_files("AoE2ScenarioParser") + collect_data_files("mgz") + collect_data_files("aocref"))   # mgz reads aocref
HIDDEN = collect_submodules("AoE2ScenarioParser") + collect_submodules("mgz") + ["aocref"]   # imported in functions, by name


def analysis(script):
    return Analysis([os.path.join(ROOT, script)], pathex=[ROOT], datas=DATAS, hiddenimports=HIDDEN,
                    excludes=["pytest"], noarchive=False)


gui, cli = analysis("gui.py"), analysis("aoe2mc.py")


def exe(a, name, console):
    return EXE(PYZ(a.pure), a.scripts, [], exclude_binaries=True, name=name, console=console, upx=False)


coll = COLLECT(exe(gui, "aoe2mc-gui", False), gui.binaries, gui.datas,
               exe(cli, "aoe2mc", True), cli.binaries, cli.datas, name="aoe2mc", upx=False)
