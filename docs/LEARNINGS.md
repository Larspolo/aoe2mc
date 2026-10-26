# Learnings

The agent writes here what it learned the hard way. Each line must save time in a later session.
Ticket runs: add new lines at the end of a section and do not change other lines (`merge=union` in `.gitattributes`
keeps the lines of both sides). The `improve` skill merges lines and keeps the file below 80 lines.

## Environment

- GitHub raw files, PyPI and the Mojang hosts (`piston-meta`, `piston-data`, `libraries.minecraft.net`) work.
  Blocked: `minecraft.wiki`, `minecraft.net`, `papermc.io` (use `misode/mcmeta`, branch `<version>-summary`, and the
  real server: `docs/minecraft-versions.md`, "Method"), AoE2 wiki HTML (use `tools/refimage.py`, MediaWiki API) and the
  record hosts (`aoe.ms`, `data.aoe2companion.com`, `www.aoe2insights.com`).
- `/root/.local/bin/pytest` and `/usr/bin/pip` use another Python: use `python3 -m pytest`, `python3 -m pip`. "cannot import
  name '_imaging' from 'PIL'": `python3 -m pip install --ignore-installed pillow`. `mgz` needs
  `python3 -m pip install --ignore-installed setuptools` first.
- Minecraft 26.3 (the default) needs Java 25 (`scripts/cloud-setup.sh`, #195). Send `stop` only after "Done (" is in
  `logs/latest.log`. Do not use `pkill -f server.jar`: it kills your own shell. A `&` job ignores SIGINT: test Ctrl-C
  with `Popen(..., start_new_session=True)` and `os.killpg(pid, SIGINT)` (#137).
- GitHub in cloud sessions: `gh api repos/Larspolo/aoe2mc/...` (REST) works. GraphQL (`gh issue list`, `gh pr create`),
  `search/...` and branch deletes give 403. A push to a new ref works, a non-fast-forward push fails: `tools/claim.py`
  uses it as a lock (#211). REST ref paths: `git/refs/heads/...`. `urllib` with a JSON body needs
  `Content-Type: application/json`, else 415 (#345).
- Quote the heredoc tag (`<<'EOF'`) for GitHub text: `<<EOF` runs each `` `name` `` as a command.
- Private repository: a workflow with a `permissions:` block also needs `contents: read`; the `pulls` API needs
  `pull-requests: read`. A new `workflow_dispatch` workflow runs only after the merge to `main` (#207).
- Minecraft server: a bad property value (`facing=up`) loads silently as the default state. An unknown block gives
  "Recoverable errors when loading section", an unknown block entity id "Skipping block entity with invalid type"
  (26.3 has no `bed` block entity, #249). A missing `level.dat` compound gives "key missing: <name>" (#60). A bad
  datapack file stops the server. A datapack `worldgen/` file makes the client warn "Experimental Settings" (#218).
  The 26.3 server writes a missing `white-list` as `true`: write `white-list=false` (`game/run.py`, #285).
- Minecraft client (#178, #179): `tools/mc_shot.py` runs it in `Xvfb`. 26.3 needs `mesa-vulkan-drivers` (lavapipe) and
  a placeholder for the title panorama. The view ends at about 100 blocks: put `--at` near the subject (#208).
- Test data: `samples/de-64.3.aoe2record` (`mgz`, MIT, #134; each town center 4 times, #139). `parse_match(f).actions`:
  `ERROR` actions are commands mgz could not read (all `DE_QUEUE` in DE 64.3: `aoe2mc.de_queue`; raw bytes: a wrapper
  of `mgz.fast.parse_action`, #372). Old `.scx` (no license, do not commit): GitHub raw
  `SiegeEngineers/genie-rs/master/crates/genie-scx/test/scenarios/` (format 1.21: `Age of Heroes b1-3-5.scx`).
- `tools/claim.py` names the run by the local branch (`who()`): beat only from the session branch, never in parallel (#361).
- The cloud clone is shallow: `git fetch --unshallow origin` before a scan of the history (#367).
- Starting runs: `mcp__claude-code-remote__fire_trigger` is in every run's tool list but can be deferred. Load it with
  `ToolSearch` (`select:mcp__claude-code-remote__fire_trigger`); runs that skipped this did not start successors (2026-10-26).
- Quota usage: `claude -p ... --output-format stream-json --verbose` prints a `rate_limit_event` with
  `unifiedWindows.five_hour/seven_day.utilization` and `resetsAt` (`tools/usage.py`). A `statusLine` does not run in cloud sessions.
- `pyproject.toml` `addopts` has `-q`: `python3 -m pytest -q` gives `-qq`, without the "N passed" line. Wait for the
  exit code, not for "passed" in the output; foreground `sleep` is blocked: use `run_in_background` (#413).
- `mcp__github__get_job_logs` gives HTTP 404 for the jobs of `ci.yml` (2026-10-26, #443): do not retry. Run its steps
  (`ruff`, fast, `-m slow`, `-m mc`) locally on the run's `head_sha`; main is red only when one fails there.

- Paper: `fill.papermc.io/v3/projects/paper/versions/V/builds/latest` lists the builds, but the jar URL is on `fill-data.papermc.io`, which the proxy blocked on 2026-10-26 (#439). Test a download host with `curl`, not only the API.
- The Paper API answers 403 to the `Python-urllib` User-Agent (`curl` works): send a User-Agent (`game/run.py` `AGENT`). `-DbundlerRepoDir=DIR` keeps the patched Mojang jar of Paper in DIR; Paper writes `usercache.json` next to the `--universe` world (#434).
- Paper plugin (#435): `game/run.py` builds `game/plugin` with `./gradlew --no-daemon -q jar` and `JAVA_HOME` = the JDK 25 (`openjdk-25-jdk-headless`: the paper-api 26.3 classes are Java 25, javac 21 cannot read them); first build 30 s. A NoAI mob finds no path before its first AI tick; the path search ends at about `follow_range` (cow: 16). The world border stops paths: test inside the map. `fill ... hollow` also fills the bottom and top faces.
## Libraries

- AoE2ScenarioParser 0.9.8 makes new scenarios (`tools/scenarios.py`: `new_scenario`, `add_unit`, `save`). It prints much
  text (`redirect_stdout`), default players are RANDOM (`western`), and `write_to_file` writes the output file name into
  the file: for the same bytes use `scenarios.save(..., name)` (#204).
- The server drops entity tags that it does not know, without a log line: let the server save the world and compare
  the entity NBT (`docs/minecraft-versions.md`). A wrong tag type gives "Serialization errors" (`mc_check.py`).
  New entity NBT: convert a map with one unit per type (`add_unit` in a loop) and run `tools/mc_check.py` (1 min).
- PrismarineJS `data/pc/common/protocolVersions.json` has the data versions of all releases (26.3 = 5023).
- `mgz.model.parse_match` reads only DE 13.34 and later; `mgz.summary.full.FullSummary` reads HD, UserPatch and older DE
  but skips the GAIA trees (`aoe2mc.read_old_record` turns the skip off). More test records: GitHub raw
  `happyleavesaoc/aoc-mgz/master/tests/recs/` (table in `docs/research/replays.md`, #376). `construct` 2.8: `IfThenElse` is a `Switch`.
- Record commands: the `player` of an mgz action is not always right (a MOVE shows for both players), and the
  `objects` of SPECIAL are not IDs. New objects take the next free ID: `aoe2mc.name_timeline` (#407).

## Code

- AoE2 map orientation (#23): tile (0, 0) is the left corner of the screen, (max, 0) the top. Block x = east, z = south:
  the world is turned 45°, not mirrored; the AoE2 top corner is in the north-east (`SPAWN_YAW`). Do not trust the axis
  gate names: `plan_walls` uses the walls next to the gate. `--orientation` turns the tile grid (`turn_map`) and each
  building canvas (`buildings.turn`); gates, walls and bridges follow their neighbours.
- Real maps have all water at elevation 0 (#164). `terrain_style`: an earlier rule wins (#5). `columns()` in
  `tests/test_terrain.py` makes `Columns` from a terrain array. Maps of one size draw the same random numbers.
- `place_objects` without a scenario: one object dict (`kind`, `name`, `player`, `x`, `y`, `rotation`, `hero`,
  `garrisoned`) on a 16 × 16 `Columns`. Buildings (also `FISH_TRAP`, docks) need `kind="B"`. `build_chunk` returns
  `(nbt, vol)`: test exact blocks with `vol` (#19). Footprint rule: `Edits.add` keeps a block outside the footprint
  when `y >= cols.wtop + E.HEAD`. Match a block by its name before `[` (`water_cauldron` starts with `water`, #295).
  A `MONUMENTS` object goes to `place_building` as a copy without `o["footprint"]`: use `buildings.footprint(name)` (#296).
- A new runtime data file (like `tools/mcdata/26.3.json`) must go into the package data (`pyproject.toml`).
- Generated on main, not in PRs: the column "Used today in" of `docs/DESIGN.md` (`tools/feature_table.py`), `docs/coverage.md`
  and `MAX` in `tests/test_coverage.py` (`coverage.yml`, #233, #234). A conflict there: take main's side.
- Block IDs in `B` depend on earlier tests: draw random numbers in state-name order, not ID order (a cause of full-suite-only failures, #44).
- An invalid item in a block entity can vanish without a log line. `tools/mc_check.py W --keep DIR` keeps the saved world
  (#27). 26.3 saves a default state as the bare name and in another property order: normalize before you compare (#189).
- Inside of a design: `tools/render.py building NAME OUT.png --cut 2` (#265); exact layers: `c.get(x, y, z)` on a `Canvas`
  (#255). `vary()` materials: `render.building_blocks(NAME, arch, variant=v)` (#146). `render.py world` draws Y >= 50
  (`--y0 -64` for `--border`); `--scale 4` gives about 800 px like `docs/images/` (#262).
- `aoe2mc.json`: object kind is `"unit"`; "ground" over a footprint is the top of the barriers: take the free cells next
  to it (`Map.around`, #307). Stump names: `STUMP`, `*_STUMP`. The `buildings` scenario: building i of `BuildingInfo` is
  near tile (4 + i % 40 × 7, 4 + i // 40 × 7) (#251).
- Parallel sibling tickets: before you add a helper or a tool option, `git fetch origin main` and grep for it (two runs
  added `render.py --cut` and a `furnish()`; the second `furnish()` broke main, #263). Put the tests of a ticket in a new
  file `tests/test_<topic>.py`: tests appended at the end of a shared file conflict (3 times on #295).
- A datapack `load` function or an RCON `@e` selector sees only entities of loaded chunks: 26.3 loads none without a
  player. In an RCON check, `forceload add X0 Z0 X1 Z1` (at most 256 chunks per command) first (#358).
- A fruit bush of `place_objects` is at block `int(x * T)` (the tile center), not at `int(tile) * T`. In `aoe2mc.json`
  the "ground" of a blocked footprint is the barrier top: take the ground of `Map.around()` (#391).
- `build.place` draws the design with `replay.Replay.building`: fake `aoe2mc.json` data in tests needs `level_height`
  and a tile size of 4 (at tile size 1 most designs give no blocks). The site keeps the commands, bottom up (#418).
- `aoe2mc.json` objects: `"id"` is the AoE2 type constant, not the object ID of a record: that is `"ref"` (#408).
  Import cycle `gather` → `build` → `replay`: `replay` imports `gather` inside a function.
- `gather.Map.path` on a whole record map (480 × 480): A* with a cell limit, about 45 ms per path, 0.3 s across the
  map. Replay paths cost 18 s per 200 s of game in samples/ (one search per unit of a group, #409).
- "units in a block": `AOE2MC_DEBUG=1` names the block; list the `aoe2mc.json` objects with a `tile` near the unit to
  find its source (#415: a `PLANT_SHRUB` on the same block, not the tree that the ticket named).
- Stacked `cylinder`s of falling height make a flat top (the outer disc covers the inner ones): use `seats()`, which
  carves air above each row (#451). Find the edge of a round room by a scan with `c.get` from the centre (`arena_inside`).
- `Canvas.furniture` sets only into `air` cells: an open design without `room()` has empty cells (`-1`), so its
  furniture vanishes without an error. Set those cells with `c.get(...) in (-1, air)` (`pagan_shrine`, #450).
- `render.py --cut` does not show the inside of a narrow tower (#452): filter `render.building_blocks()` by x, y, z
  (drop barriers and one side of the walls) and call `render.render()` for a section view.
- `render.building_blocks` gives states with the `minecraft:` prefix and world y (the ground is y 63, canvas y 1 is y 64): strip the prefix before you match a name (#449).
- Furniture inside a closed design: a text map of each layer (one character per state name of `render.building_blocks`, rows by z) shows the positions faster than an isometric render, which hides small blocks behind walls (#501).
- `tests/test_objects.py::test_blocks_under_water_are_waterlogged` names the blocks of `fish_trap`: change it with the fish trap materials (#486). Grep `tests/` for the design name before the full run.
