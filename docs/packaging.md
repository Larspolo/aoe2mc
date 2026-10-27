# App bundles

An app bundle is one folder that runs aoe2mc without Python on the computer (#1541, part of #1539).
The folder `aoe2mc` holds two programs:

- `aoe2mc-gui` (Windows: `aoe2mc-gui.exe`): the converter window (`gui.run`, #1540).
- `aoe2mc` (Windows: `aoe2mc.exe`): the command line (`aoe2mc.main`), the same as `python3 aoe2mc.py`.

## Build a bundle locally

PyInstaller makes a bundle only for the system that it runs on.

1. Install the build dependencies: `python3 -m pip install -r packaging/requirements.txt`.
2. Build: `python3 -m PyInstaller --noconfirm packaging/aoe2mc.spec`. The bundle is in `dist/aoe2mc`, the build files
   are in `build/` (both are ignored by git). Use `--distpath out/dist --workpath out/build` to put them in `out/`.
3. Test: `dist/aoe2mc/aoe2mc samples/test_village.aoe2scenario OUTWorld` and
   `dist/aoe2mc/aoe2mc samples/de-64.3.aoe2record OUTWorld2`. Each world must have `level.dat` and `region/*.mca` files.

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

The spec also adds all submodules of `AoE2ScenarioParser` and `mgz` as hidden imports: `aoe2mc.py` imports them in
functions.

## Workflow

`.github/workflows/bundles.yml` builds the bundle on four runners: `windows-latest`, `macos-latest` (arm64),
`macos-15-intel` (x86_64; `macos-13` is retired) and `ubuntu-22.04` (an old glibc, so the bundle runs on more Linux
systems). It starts by hand (`workflow_dispatch`), from the release workflow (`workflow_call`, #1542) and on a PR that
changes `packaging/` or the workflow. Each job converts the two samples with the frozen command line. The Linux job
also opens the frozen window under `xvfb-run`. Each job uploads its folder as the artifact `aoe2mc-<os>-<arch>`.

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
