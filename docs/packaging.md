# App bundles

An app bundle is one folder that runs aoe2mc without Python on the computer (#1541, part of #1539).
The folder `aoe2mc` holds three programs:

- `aoe2mc-gui` (Windows: `aoe2mc-gui.exe`): the converter window (`gui.run`, #1540).
- `aoe2mc` (Windows: `aoe2mc.exe`): the command line (`aoe2mc.main`), the same as `python3 aoe2mc.py`.
- `aoe2mc-game` (Windows: `aoe2mc-game.exe`): the game program (`game/run.py` `main`, #1778), the same as
  `python3 game/run.py`. The tab "Play" of the window starts it next to itself (`gui.game_command`). It needs a Java
  runtime (it downloads a Temurin JRE when none is there, `mc_check.java_for`), but no JDK: the bundle has the Paper
  plugin jar. Its server folders go to the user cache (`~/.cache/aoe2mc/servers`), not into the bundle.

## Build a bundle locally

PyInstaller makes a bundle only for the system that it runs on.

1. Install the build dependencies: `python3 -m pip install -r packaging/requirements.txt`.
2. Build the plugin jar (a JDK 25): `cd game/plugin && ./gradlew --no-daemon -q jar && cp build/libs/aoe2mc-plugin.jar .`
   Without `game/plugin/aoe2mc-plugin.jar` the bundle has no plugin, and `aoe2mc-game` fails at the server start.
3. Build: `python3 -m PyInstaller --noconfirm packaging/aoe2mc.spec`. The bundle is in `dist/aoe2mc`, the build files
   are in `build/` (both are ignored by git). Use `--distpath out/dist --workpath out/build` to put them in `out/`.
4. Test: `dist/aoe2mc/aoe2mc samples/test_village.aoe2scenario OUTWorld` and
   `dist/aoe2mc/aoe2mc samples/de-64.3.aoe2record OUTWorld2`. Each world must have `level.dat` and `region/*.mca` files.
   The game program: `dist/aoe2mc/aoe2mc-game OUTWorld --bench 10` from another folder than the checkout.

The window needs a Python with tkinter. Without tkinter, PyInstaller prints "tkinter installation is broken" and the
window does not start, but the command line works.

## Data files of the spec

A missing data file gives an error only at run time, when a conversion reads it. So the workflow converts a scenario
and a record. `packaging/aoe2mc.spec` puts these data files in the bundle:

| Data files | Who reads them |
|---|---|
| `tools/mcdata/26.3.json` | `aoe2mc.py` (the block states of Minecraft 26.3), next to itself |
| the data files of `AoE2ScenarioParser` | the scenario reader |
| the data files of `mgz` | the record reader |
| the data files of `aocref` (`data/constants.json`, `data/datasets/*.json`) | `mgz.reference` (records) |
| `game/data/*.jsonl` (as `data/*.jsonl`: train, units, buildings, civs) | `game/table.py` and `game/train.py`, next to themselves (#1913) |
| `game/plugin/aoe2mc-plugin.jar` (as `plugin/aoe2mc-plugin.jar`) | `game/run.py` `plugin_jar` in a frozen app |

The spec also adds all submodules of `AoE2ScenarioParser` and `mgz` as hidden imports: `aoe2mc.py` imports them in
functions. The modules of `game/` and `tools/` import each other by their short names, so `game/` and `tools/` are on
the `pathex` of each analysis.

## Workflow

`.github/workflows/bundles.yml` builds the bundle on four runners: `windows-latest`, `macos-latest` (arm64),
`macos-15-intel` (x86_64; `macos-13` is retired) and `ubuntu-22.04` (an old glibc, so the bundle runs on more Linux
systems). It starts by hand (`workflow_dispatch`), from the release workflow (`workflow_call`, #1542) and on a PR that
changes `packaging/` or the workflow. Each job builds the plugin jar with a JDK 25 (`actions/setup-java`) and converts
the two samples with the frozen command line. The Linux job also opens the frozen window under `xvfb-run`, and starts
the frozen game program on a converted `tiny` world from another folder: `--bench 10`, then a typed plugin command
(`aoe stance`) that answers only when the plugin of the bundle loaded. Each job uploads its folder as the artifact `aoe2mc-<os>-<arch>`.

## Installers

Each job of `bundles.yml` then makes the installer of its system from the bundle, installs it as a user would and
converts `samples/test_village.aoe2scenario` with the installed command line (#1542). It uploads the installer as the
artifact `installer-<os>-<arch>`. The version is the tag without `v` (`0.0.0-dev` on a branch).

| System | Installer | Made with | Test in the job |
|---|---|---|---|
| Windows | `aoe2mc-<version>-windows-x64-setup.exe` | Inno Setup, `packaging/windows.iss`: a per-user install (no admin), a Start menu item, an uninstaller | `/VERYSILENT /DIR=...` |
| macOS | `aoe2mc-<version>-macos-arm64.dmg`, `...-macos-x86_64.dmg` | the `BUNDLE` of `packaging/aoe2mc.spec` (`aoe2mc.app`) in `hdiutil create` | `hdiutil attach`, copy the app |
| Linux | `aoe2mc-<version>-linux-x86_64.AppImage` | `appimagetool` 1.9.0, `packaging/AppRun` (arguments: the command line, none: the window), `packaging/aoe2mc.desktop` | `--appimage-extract` |

`packaging/icon.py` draws the icon (an own image: a grass block with a tower) as `icon.png`, `icon.ico` and
`icon.icns` before the build; these files are not in git. The installers are not signed (the owner chose this in
#1544): the README section "Install" tells the user how to go past the warning.

`.github/workflows/installers.yml` runs on a tag `v*`: it calls `bundles.yml` and attaches the four installers to the
release of the tag. `worlds.yml` also runs on the tag and attaches the example worlds to the same release.

## Pitfalls

- The default `python3` (3.11, `/usr/local/bin`) has no `tkinter`, also after `apt-get install -y python3-tk`: that gives it to `/usr/bin/python3.12` only. Test a Tk window with a 3.12 venv (`/usr/bin/python3.12 -m venv V && V/bin/python -m pip install -r requirements.txt pytest`) and `xvfb-run -a` (#1540).
- Automerge waits only for `quick`: a PR that changes `packaging/` or a workflow with its own PR checks (`Bundles`) gets `hold` until those checks are green (#1599: two of four jobs failed first).
- Actions artifacts (`/actions/artifacts/ID/zip`) do not download in the cloud: the proxy blocks `*.blob.core.windows.net`; release assets (`github.com/.../releases/download/...`) work. Check a bundle with a local build (`packaging/aoe2mc.spec` in a 3.12 venv, `apt-get install -y python3-tk` first). The auto mode denies running a downloaded `appimagetool`. Under Xvfb (no window manager) no field has the key focus: click into each field with `xdotool mousemove X Y click 1` before `xdotool type` (#1545).
- Click through the window without `xdotool`: in a script under `xvfb-run -a /usr/bin/python3.12`, `w = gui.window()`, walk `winfo_children()`, `invoke()` the `TButton` by its `cget("text")`, and loop `w.update()` while you read the log `Text` (#1775: a game start and stop on the `tiny` world, 2 minutes).
- The bundle puts the data of `game/data` into `game_data` (`table.FROZEN`), not `data`: `data/` has files of the same names (`train.jsonl`, `units.jsonl`), and one replaced the other (`KeyError` in `civs.py`, #2839). `aoe2mc-game --help` does not show it: start it on a world (`--bench 10`); without the plugin jar it stops at `plugin/aoe2mc-plugin.jar` after all imports.
- A windowed program (`aoe2mc-gui.exe`, `pythonw`) cannot send Ctrl-Break to a child that has its own console: `GenerateConsoleCtrlEvent` reaches only the console of the caller. `gui.stop_game` writes `STOP_LINE` to the stdin of the game program on Windows, and `taskkill /T /F` ends the tree with the Java server after the wait (#3003; check: `packaging/stop_check.py` in the Windows job of `bundles.yml`).
