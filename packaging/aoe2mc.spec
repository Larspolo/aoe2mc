# PyInstaller spec of the app bundle (#1541): one folder "aoe2mc" with the window (aoe2mc-gui, gui.run of #1540), the
# command line (aoe2mc, aoe2mc.main) and the game program (aoe2mc-game, game/run.py main, #1778).
# Build: python3 -m PyInstaller packaging/aoe2mc.spec (docs/packaging.md).
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.dirname(SPECPATH)
# aoe2mc.py reads tools/mcdata/26.3.json next to itself; the parsers read their own data files (a missing file gives
# an error only at run time, so the workflow converts a scenario and a record)
DATAS = ([(os.path.join(ROOT, "tools", "mcdata", "26.3.json"), os.path.join("tools", "mcdata"))]
         + [(os.path.join(ROOT, "data", "*.jsonl"), "data")]   # units.py reads them (#1917)
         + collect_data_files("AoE2ScenarioParser") + collect_data_files("mgz") + collect_data_files("aocref"))   # mgz reads aocref
HIDDEN = collect_submodules("AoE2ScenarioParser") + collect_submodules("mgz") + ["aocref"]   # imported in functions, by name
# the game program: the modules of game/ and tools/ import each other by their short names (run.py puts both folders
# on sys.path), so they are top-level modules of the bundle, and their data goes next to them. The plugin jar comes
# from the workflow (gradlew jar): game/run.py takes it in a frozen app, so the user needs a Java runtime, no JDK.
GAME = os.path.join(ROOT, "game")
JAR = os.path.join(GAME, "plugin", "aoe2mc-plugin.jar")
# all data files of game/data (table.load: train, units, buildings; #1913), in their own folder: data/ has files of the
# same names (table.FROZEN, #2839)
GAME_DATAS = (DATAS + [(os.path.join(GAME, "data", "*.jsonl"), "game_data")]
              + [(os.path.join(GAME, "data", "antiquity", "*.jsonl"), os.path.join("game_data", "antiquity"))]   # #3666
              + [(JAR, "plugin")] * os.path.exists(JAR))
# the tag and the SHA-1 of the resource pack of the release (the workflow writes it on a tag, run.RELEASE, #2741)
RELEASE = os.path.join(ROOT, "packaging", "release.json")
GAME_DATAS += [(RELEASE, ".")] * os.path.exists(RELEASE)


def analysis(script, datas=DATAS):
    return Analysis([os.path.join(ROOT, script)], pathex=[ROOT, GAME, os.path.join(ROOT, "tools")], datas=datas,
                    hiddenimports=HIDDEN, excludes=["pytest"], noarchive=False)


gui, cli, game = analysis("gui.py"), analysis("aoe2mc.py"), analysis(os.path.join("game", "run.py"), GAME_DATAS)


# the icon of packaging/icon.py (the workflow draws it first, #1542); a local build without it has the default icon
ICON = os.path.join(ROOT, "packaging", "icon.ico" if sys.platform == "win32" else "icon.icns")
ICON = ICON if os.path.exists(ICON) else None


def exe(a, name, console):
    return EXE(PYZ(a.pure), a.scripts, [], exclude_binaries=True, name=name, console=console, upx=False, icon=ICON)


coll = COLLECT(exe(gui, "aoe2mc-gui", False), gui.binaries, gui.datas,
               exe(cli, "aoe2mc", True), cli.binaries, cli.datas,
               exe(game, "aoe2mc-game", True), game.binaries, game.datas, name="aoe2mc", upx=False)
if sys.platform == "darwin":                                            # the app in the .dmg of the installer (#1542)
    app = BUNDLE(coll, name="aoe2mc.app", icon=ICON, bundle_identifier="io.github.larspolo.aoe2mc",
                 info_plist={"CFBundleExecutable": "aoe2mc-gui", "CFBundleDisplayName": "aoe2mc",
                             "NSHighResolutionCapable": True})
