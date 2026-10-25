# Learnings

The agent writes here what it learned the hard way. Each line must save time in a later session.
Keep this file below 80 lines: merge similar lines and remove lines that are no longer true.

## Environment

- GitHub raw files, PyPI and the Mojang hosts (`piston-meta`, `piston-data`, `libraries.minecraft.net`) work.
- `/root/.local/bin/pytest` and `/usr/bin/pip` use another Python: use `python3 -m pytest`, `python3 -m pip`. "cannot import
  name '_imaging' from 'PIL'": the Debian pillow shadows it: `python3 -m pip install --ignore-installed pillow`.
- `minecraft.wiki`, `minecraft.net` and `papermc.io` are blocked (curl and WebFetch). For Minecraft facts use
  the Mojang data reports in `misode/mcmeta` (GitHub raw, branch `<version>-summary`) and the real server
  (see `docs/minecraft-versions.md`, "Method").
- Java 21 is installed. Minecraft 26.3 needs Java 25: `apt-get install -y openjdk-25-jre-headless`. Send `stop` to a
  server only after "Done (" is in `logs/latest.log`. Do not use `pkill -f server.jar`: it also kills your own shell.
- GitHub in cloud sessions: `gh api repos/Larspolo/aoe2mc/...` (REST) works. GraphQL (`gh issue list`,
  `gh pr create`), `search/...` and deleting a branch give 403. CI job logs: only `mcp__github__get_job_logs`.
- Quote the heredoc tag (`<<'EOF'`) for GitHub text: in `<<EOF` the shell runs each `` `name` `` as a command
  and the text loses the names. Pass paths as arguments instead of `$VAR` in the text.
- Scheduled runs can have no MCP connector tools. The `autopilot` skill has a REST table for that case.
- A scheduled task that `create_trigger` made has no repository and its sessions cannot clone: set
  `Larspolo/aoe2mc` as its repository in the claude.ai UI. Scheduled runs use Sonnet 5.5 unless the task sets a model.
- The repository is private: a workflow with a `permissions:` block also needs `contents: read`, or
  `actions/checkout` fails with "Repository not found". The `pulls` API needs `pull-requests: read` (else 403).
- Minecraft server: a bad property value (`facing=up`) loads silently as the default state. An unknown block gives
  "Recoverable errors when loading section", a missing `level.dat` compound "key missing: <name>". The yggdrasil key error is normal.
- AoE2 wiki: HTML pages give 403 (Cloudflare). Use `tools/refimage.py` (MediaWiki API, own `User-Agent`). Page text:
  `api.php?action=parse&page=Title&prop=wikitext&format=json&formatversion=2`.
- AoE2 recorded games: the record hosts (`aoe.ms`, `data.aoe2companion.com`, `www.aoe2insights.com`) are blocked. Only the owner can add a record (#134).
- Java 21 is installed. Minecraft 26.3 needs Java 25: `apt-get install -y openjdk-25-jre-headless`. Send `stop` only
  after "Done (" is in `logs/latest.log`. Do not use `pkill -f server.jar`: it also kills your own shell.
- GitHub in cloud sessions: `gh api repos/Larspolo/aoe2mc/...` (REST) works. GraphQL (`gh issue list`,
  `gh pr create`) and `search/...` give 403. CI job logs: only `mcp__github__get_job_logs`.
- Quote the heredoc tag (`<<'EOF'`) for GitHub text: `<<EOF` runs each `` `name` `` as a command. Pass paths as arguments.
- Deleting a branch through the proxy gives 403: skip it. Without MCP tools use the REST table in `autopilot`.
- A scheduled task from `create_trigger` has no repository, so its sessions cannot clone: set `Larspolo/aoe2mc`
  as its repository in the claude.ai UI. Scheduled runs use Sonnet 5.5 unless the task sets another model.
- The repository is private: a workflow with a `permissions:` block also needs `contents: read`, or
  `actions/checkout` fails with "Repository not found". The `pulls` API needs `pull-requests: read` (else 403).
- Minecraft server: a bad property value (`facing=up`) loads silently as the default state. An unknown block gives
  "Recoverable errors when loading section". A missing `level.dat` compound gives "key missing: <name>" (#60).
  The yggdrasil key error is normal: `api.minecraftservices.com` is not reachable.
- AoE2 wiki: HTML pages give a Cloudflare challenge (403). The MediaWiki API works: `ageofempires.fandom.com/
  api.php?action=query&titles=File:Castle_aoe2DE.png&prop=imageinfo&iiprop=url&format=json` gives the image URL
  on `static.wikia.nocookie.net` (WebP). Page text: `action=parse&page=Title&prop=wikitext&format=json&formatversion=2`.
  Python `urllib` with the default User-Agent gets 403: use `curl`, or send another `User-Agent`
  (see `tools/refimage.py`).
- AoE2 recorded games: the record hosts (`aoe.ms`, `data.aoe2companion.com`, `www.aoe2insights.com`) are blocked.
  The `mgz` test records on GitHub raw work (`happyleavesaoc/aoc-mgz/master/tests/recs/de-64.3.aoe2record`, MIT):
  `mgz.model.parse_match(f).map.tiles` gives terrain and elevation of a real DE map. Install `mgz` after
  `python3 -m pip install --ignore-installed setuptools` (the Debian setuptools cannot build it).

## Libraries

- AoE2ScenarioParser 0.9.8 can make new scenarios: `AoE2DEScenario.from_default()`, then
  `map_manager.map_size = N`, `unit_manager.add_unit(PlayerId, ID, x=, y=)`, `write_to_file(path)`.
  It prints much text: wrap calls in `contextlib.redirect_stdout(io.StringIO())`. In a default scenario all players
  have civilization RANDOM, so all buildings use the `western` set.
- The server drops entity tags that it does not know, without a log line. To check a new entity format, let the
  server save the world and compare the entity NBT before and after (method in `docs/minecraft-versions.md`).
  A tag with a wrong type gives "Serialization errors" (WARN), which `tools/mc_check.py` finds.
- `tools/fetch_mcdata.py` reads the exact Mojang data from `misode/mcmeta`. PrismarineJS lags behind; its
  `data/pc/common/protocolVersions.json` has the data versions of all releases (26.3 = 5023).

## Code

- AoE2 map orientation (#23): tile (0, 0) is the left corner of the screen, (max, 0) the top (parser `area.py`
  `CORNERS`; openage: axes NE, SE). Block x = east, z = south: the world is turned 45°, not mirrored; the AoE2 top
  corner is in the north-east. The spawn looks north-east like the AoE2 camera (`SPAWN_YAW`). Gates `WEST_TO_EAST`
  and `NORTH_TO_SOUTH` are diagonal. Do not trust the axis gate names (`samples/gallery` has a `NORTHWEST_TO_SOUTHEAST`
  gate along tile x): `plan_walls` uses the walls next to the gate. `--orientation` turns the
  tile grid (`turn_map`) and each building canvas (`buildings.turn`); gates, walls and bridges follow their neighbours.
- The tiny scenario has only a town center, a house and a barracks: to see the golden test fail, change the house chimney.

- Water (#164, `docs/research/water.md`): AoE2 has no water level. In the samples and two real DE maps all water is at
  elevation 0; trenches come from high land next to the water.
- The tiny scenario has a town center, a house and a barracks: change the house chimney to see the golden test fail.
- Test terrain code without a scenario: `columns()` in `tests/test_terrain.py` makes `aoe2mc.Columns` from a
  small terrain array. Maps of the same size draw the same random numbers, so two maps can be compared per block.
- `place_objects` without a scenario: call it with one object dict (`kind`, `name`, `player`, `x`, `y`,
  `rotation`, `hero`, `garrisoned`) on a 16 × 16 `Columns`. With `sys.settrace` this shows which branch each
  `OtherInfo` name takes (#6). Buildings (also `FISH_TRAP`, docks) need `kind="B"`, else nothing is placed.
  `build_chunk` returns `(nbt, vol)`: test exact blocks of a chunk with `vol` (#19).
- `aoe2mc.py` reads `tools/mcdata/1.21.1.json` at import (#19). The package ships it as `tools.mcdata`
  (`pyproject.toml`). A new runtime data file must go into the package data too (test: `pip install .` in a venv).
- `terrain_style` checks names in sequence: an earlier rule wins (`ROAD_GRAVEL` matched `GRAVEL` until #5).
- `.gitattributes` merges `docs/LEARNINGS.md` and `docs/DESIGN.md` with `union` (both sides kept, #76): after a merge,
  look for two versions of one line and keep one. GitHub still shows the PR as `dirty`: merge `origin/main` locally.
- A merge conflict in `docs/coverage.md`: take any side, run `python3 tools/coverage.py`, then set `MAX` in
  `tests/test_coverage.py` to the new counts. Parallel runs often change the same counts (#79). Check
  `mergeable_state` before the merge: a green PR is "dirty" when main moved after the push.
- All 243 building types of one set draw in about 1 s; the gallery converts in about 23 s (`--verbose`: per phase, #26).
- Block IDs in `B` depend on what was registered before (earlier tests or conversions). Code that draws random
  numbers per block ID must go in state-name order, not ID order (see #44). A test that passes alone but
  fails in the full suite often has this cause.
- An invalid item in a block entity can vanish without a log line. `tools/mc_check.py W --keep DIR` keeps the world
  that the server saved: read the block entity there (1.21.1 saves the loaded chunks again, 26.3 can skip them) (#27).
- To check new entity NBT, make a map with one unit per type (`unit_manager.add_unit` in a loop), convert it and run
  `tools/mc_check.py` on it: about 1 minute.
