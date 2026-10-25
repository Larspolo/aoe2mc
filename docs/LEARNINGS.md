# Learnings

The agent writes here what it learned the hard way. Each line must save time in a later session.
Keep this file below 80 lines: merge similar lines and remove lines that are no longer true.

## Environment

- GitHub raw files, PyPI and the Mojang hosts (`piston-meta`, `piston-data`, `libraries.minecraft.net`) work.
- `/root/.local/bin/pytest` and `/usr/bin/pip` use another Python. Use `python3 -m pytest` and `python3 -m pip`.
  Symptom: "cannot import name '_imaging' from 'PIL'" in the end-to-end tests. If it stays after the install,
  the old Debian pillow shadows it: `python3 -m pip install --ignore-installed pillow`.
- `minecraft.wiki`, `minecraft.net` and `papermc.io` are blocked (curl and WebFetch). For Minecraft facts use
  the Mojang data reports in `misode/mcmeta` (GitHub raw, branch `<version>-summary`) and the real server
  (see `docs/minecraft-versions.md`, "Method").
- Java 21 is installed in the cloud container. Minecraft 1.21.1 needs Java 21, 26.3 needs Java 25
  (`javaVersion.majorVersion` in the version JSON): `apt-get install -y openjdk-25-jre-headless` works.
  The Mojang hosts are allowed since #12. Send `stop` to a server only after "Done (" is in `logs/latest.log`
  (earlier input is lost). Do not use `pkill -f server.jar`: it also kills your own shell.
- GitHub in cloud sessions: `gh api repos/Larspolo/aoe2mc/...` (REST) works. GraphQL (`gh issue list`,
  `gh pr create`) and `search/...` give 403. CI job logs: only `mcp__github__get_job_logs`.
- Deleting a branch with `gh api .../git/refs/heads/B -X DELETE` gives 403 through the proxy. Skip it.
- Scheduled runs can have no MCP connector tools. The `autopilot` skill has a REST table for that case.
- A scheduled task that `create_trigger` made has no repository: its sessions have no `add_repo` tool and
  cannot clone ("GitHub access to this repository is not enabled for this session"). The scheduled task
  must have `Larspolo/aoe2mc` as its repository (set it in the claude.ai UI). Scheduled runs use Sonnet 5.5
  unless the task sets another model.
- The repository is private: a workflow with a `permissions:` block also needs `contents: read`, or
  `actions/checkout` fails with "Repository not found".

- Minecraft server: a bad property value (`facing=up`) loads silently as the default state. An unknown block
  name gives "Recoverable errors when loading section". A missing `level.dat` compound
  gives "key missing: <name>" (`DragonFight` until #60).
  The yggdrasil key error is normal: `api.minecraftservices.com` is not reachable.

- AoE2 wiki: HTML pages give a Cloudflare challenge (403). The MediaWiki API works: `ageofempires.fandom.com/
  api.php?action=query&titles=File:Castle_aoe2DE.png&prop=imageinfo&iiprop=url&format=json` gives the image URL
  on `static.wikia.nocookie.net` (WebP). Page text: `action=parse&page=Title&prop=wikitext&format=json&formatversion=2`.
  Use `curl`: Python `urllib` gets 403.

## Libraries

- AoE2ScenarioParser 0.9.8 can make new scenarios: `AoE2DEScenario.from_default()`, then
  `map_manager.map_size = N`, `unit_manager.add_unit(PlayerId, ID, x=, y=)`, `write_to_file(path)`.
  It prints much text: wrap calls in `contextlib.redirect_stdout(io.StringIO())`.
- In a default scenario all players have civilization RANDOM, so all buildings use the `western` set.
- `tools/fetch_mcdata.py` reads the exact Mojang data of each release from `misode/mcmeta` (GitHub raw).
  PrismarineJS lags behind (blocks up to 26.1). Its `data/pc/common/protocolVersions.json` has the data
  versions of all releases (26.3 = 5023).

## Code

- AoE2 map orientation (#23): tile (0, 0) is the left (west) corner of the screen, (max, 0) the top, (max, max)
  the right, (0, max) the bottom (`AoE2ScenarioParser` `area.py`, `CORNERS`). Tile x goes up-right, tile y
  down-right. Block x = east, z = south keeps the handedness: the world is turned 45°, not mirrored. The AoE2 top
  corner is the north-east corner. A 90° turn of the grid cannot make "screen up" more north than now.

- The tiny scenario has only a town center, a house and a barracks. To see the golden test fail, change a
  block that these designs draw last (for example the house chimney).

- Test terrain code without a scenario: `columns()` in `tests/test_terrain.py` makes `aoe2mc.Columns` from a
  small terrain array. Maps of the same size draw the same random numbers, so two maps can be compared per block.
- `place_objects` without a scenario: call it with one object dict (`kind`, `name`, `player`, `x`, `y`,
  `rotation`, `hero`, `garrisoned`) on a 16 × 16 `Columns`. With `sys.settrace` this shows which branch each
  `OtherInfo` name takes (#6).
  Buildings (also `FISH_TRAP`, docks) need `kind="B"`, else nothing is placed. `build_chunk` returns
  `(nbt, vol)`: test exact blocks of a chunk with `vol` (#19).
- `aoe2mc.py` reads `tools/mcdata/1.21.1.json` at import (#19). The package ships it as `tools.mcdata`
  (`pyproject.toml`). A new runtime data file must go into the package data too (test: `pip install .` in a venv).
- `terrain_style` checks names in sequence: an earlier rule wins (`ROAD_GRAVEL` matched `GRAVEL` until #5).
- A merge conflict in `docs/coverage.md`: take any side, run `python3 tools/coverage.py`, then set `MAX` in
  `tests/test_coverage.py` to the new counts. Parallel runs often change the same counts (#79). Check
  `mergeable_state` before the merge: a green PR is "dirty" when main moved after the push.
- Drawing all 243 building types for one architecture set takes about 1 s. A full gallery conversion takes
  about 30 s per set.
- Block IDs in `B` depend on what was registered before (earlier tests or conversions). Code that draws random
  numbers per block ID must go in state-name order, not ID order (see #44). A test that passes alone but
  fails in the full suite often has this cause.
- To check new entity NBT (items, variants, components), make a map with one unit per type
  (`unit_manager.add_unit` in a loop), convert it and run `tools/mc_check.py` on it: about 1 minute.
