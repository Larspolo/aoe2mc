# Learnings

The agent writes here what it learned the hard way. Each line must save time in a later session.
Ticket runs: add new lines at the end of a section and do not change other lines (`merge=union` in `.gitattributes`
keeps the lines of both sides). A pitfall of one topic (server, Paper, records, a design) goes into the "Pitfalls" section
of its document (named below): this file loads into each run. The `improve` skill merges lines and keeps it below 80 lines.

## Environment and libraries

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
- Pitfalls of the Minecraft server, client and NBT (silent defaults, dropped tags): `docs/minecraft-versions.md`; of Paper
  and the game program: `docs/research/gameplay.md`; of RCON `@e`: `docs/datapack.md` (sections "Pitfalls").
- `tools/claim.py` names the run by the local branch (`who()`): beat only from the session branch, never in parallel (#361).
  Run `claim.py N --guard` alone and read its exit code before the push: `guard; echo g=$? && git push` pushes also after
  a failed guard (#540).
- The cloud clone is shallow: `git fetch --unshallow origin` before a scan of the history (#367).
- A run of the scheduled task has only `subscribe_pr_activity` and `unsubscribe_pr_activity` of `claude-code-remote`:
  no `fire_trigger`, `send_later` or `list_triggers` (checked 2026-10-26, #566). The pacer session starts the runs.
- Quota usage: `claude -p ... --output-format stream-json --verbose` prints a `rate_limit_event` with
  `unifiedWindows.five_hour/seven_day.utilization` and `resetsAt` (`tools/usage.py`). A `statusLine` does not run in cloud sessions.
- `pyproject.toml` `addopts` has `-q`: `python3 -m pytest -q` gives `-qq`, without the "N passed" line. Wait for the
  exit code, not for "passed" in the output; foreground `sleep` is blocked: use `run_in_background` (#413).
- `mcp__github__get_job_logs` gives HTTP 404 for the jobs of `ci.yml` (2026-10-26, #443): do not retry. Run its steps
  (`ruff`, fast, `-m slow`, `-m mc`) locally on the run's `head_sha`; main is red only when one fails there.

- Paper: `fill.papermc.io/v3/projects/paper/versions/V/builds/latest` lists the builds, but the jar URL is on `fill-data.papermc.io`, which the proxy blocked on 2026-10-26 (#439). Test a download host with `curl`, not only the API.
- The Paper API answers 403 to the `Python-urllib` User-Agent (`curl` works): send a User-Agent (`game/run.py` `AGENT`). `-DbundlerRepoDir=DIR` keeps the patched Mojang jar of Paper in DIR; Paper writes `usercache.json` next to the `--universe` world (#434).
- Paper plugin (#435): `game/run.py` builds `game/plugin` with `./gradlew --no-daemon -q jar` and `JAVA_HOME` = the JDK 25 (`openjdk-25-jdk-headless`: the paper-api 26.3 classes are Java 25, javac 21 cannot read them); first build 30 s. A NoAI mob finds no path before its first AI tick; the path search ends at about `follow_range` (cow: 16). The world border stops paths: test inside the map. `fill ... hollow` also fills the bottom and top faces.
- `pytest -m mc` needs `javac` since the Paper plugin (#493): without it 14 tests fail with "no javac". Until the owner pastes setup v6 (#495), run `apt-get install -y openjdk-25-jdk-headless` (works in the cloud, 1 min, #497).
- `-m mc` takes about 21 minutes, and 14 of its tests stop with "no javac" when `/etc/aoe2mc-setup-version` is below 6: `apt-get install -y openjdk-25-jdk-headless` first (1 min, #536).
- A world that the Paper server saved does not open in the vanilla client ("Overworld settings missing"): Paper moves
  `data/minecraft/world_gen_settings.dat` into each dimension folder. Copy the `.dat` files of `data/minecraft/` of a fresh
  conversion into the saved copy before `tools/mc_shot.py` (#420, #580).

## Libraries

- `-m mc` takes about 21 minutes, and 14 of its tests stop with "no javac" when `/etc/aoe2mc-setup-version` is below 6:
  `apt-get install -y openjdk-25-jdk-headless` first (1 min, #536).
- Wait for a `run_in_background` job in the foreground: `timeout 580 bash -c 'until [ -s OUT ]; do sleep 5; done'` works; a bare `sleep` is blocked (#514).
- Records (`mgz`, test records, command pitfalls): `docs/research/replays.md`, "Pitfalls".
- AoE2ScenarioParser 0.9.8 makes new scenarios (`tools/scenarios.py`: `new_scenario`, `add_unit`, `save`). It prints much
  text (`redirect_stdout`), default players are RANDOM (`western`), and `write_to_file` writes the output file name into
  the file: for the same bytes use `scenarios.save(..., name)` (#204).

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
- Design pitfalls (stacked cylinders, furniture in open designs, render limits, tests that name design blocks):
  the `design` skill, "Pitfalls".
- Inside of a design: `tools/render.py building NAME OUT.png --cut 2` (#265); exact layers: `c.get(x, y, z)` on a `Canvas`
  (#255). `vary()` materials: `render.building_blocks(NAME, arch, variant=v)` (#146). `render.py world` draws Y >= 50
  (`--y0 -64` for `--border`); `--scale 4` gives about 800 px like `docs/images/` (#262).
- `aoe2mc.json`: object kind is `"unit"`; `"id"` is the AoE2 type constant, the object ID of a record is `"ref"` (#408).
  The "ground" of a blocked footprint is the barrier top: take the free cells of `Map.around()` (#307, #391). Stump names:
  `STUMP`, `*_STUMP`. The `buildings` scenario: building i of `BuildingInfo` is near tile (4 + i % 40 × 7, 4 + i // 40 × 7).
- Parallel sibling tickets: before you add a helper or a tool option, `git fetch origin main` and grep for it (two runs
  added `render.py --cut` and a `furnish()`; the second `furnish()` broke main, #263). Put the tests of a ticket in a new
  file `tests/test_<topic>.py`: tests appended at the end of a shared file conflict (3 times on #295).
- A fruit bush of `place_objects` is at block `int(x * T)` (the tile center), not at `int(tile) * T` (#391).
- "units in a block": `AOE2MC_DEBUG=1` names the block; list the `aoe2mc.json` objects with a `tile` near the unit to
  find its source (#415: a `PLANT_SHRUB` on the same block, not the tree that the ticket named).
- Stacked `cylinder`s of falling height make a flat top (the outer disc covers the inner ones): use `seats()`, which
  carves air above each row (#451). Find the edge of a round room by a scan with `c.get` from the centre (`arena_inside`).
- `Canvas.furniture` sets only into `air` cells: an open design without `room()` has empty cells (`-1`), so its
  furniture vanishes without an error. Set those cells with `c.get(...) in (-1, air)` (`pagan_shrine`, #450).
- `render.py --cut` does not show the inside of a narrow tower (#452): filter `render.building_blocks()` by x, y, z
  (drop barriers and one side of the walls) and call `render.render()` for a section view.
- `render.building_blocks` gives states with the `minecraft:` prefix and world y (the ground is y 63, canvas y 1 is y 64): strip the prefix before you match a name (#449).
- Items in a block of a design: the canvas turns after the design, so set the item data after `E.add` in `place_building` by world position (`buildings.SHELVES` -> `aoe2mc.BLOCK_DATA`). 26.3 shelf: block entity `shelf`, `Items` with `Slot` 0-2; the server keeps them (#526).
- `docs/coverage.md` on main is stale while GitHub Actions cannot run (#460): it listed 21 fallbacks that the code already handles. For the real fallbacks, run `python3 tools/coverage.py OUT.md` into the scratchpad (#500).
- Furniture inside a closed design: a text map of each layer (one character per state name of `render.building_blocks`, rows by z) shows the positions faster than an isometric render, which hides small blocks behind walls (#501).
- `tests/test_objects.py::test_blocks_under_water_are_waterlogged` names the blocks of `fish_trap`: change it with the fish trap materials (#486). Grep `tests/` for the design name before the full run.
- `docs/coverage.md` on main can be stale (#460): for the real fallbacks run `python3 tools/coverage.py OUT.md` (#500).
- A gate footprint is not in `cols.blocked` (units walk through the passage): `place_building` blocks only the columns with a solid block at head height (#577). Reproduce "units in a block" of a campaign with `tests/test_scx.py` `build()` and random units on the wall line.
- A change to the blocks of an object: also run the `-m mc` tests of the files that name it (`grep -l NAME tests/`): the fast suite skips them, and #590 broke `test_villager_forages_on_a_server` (fixed in #602).
- `game/gather.py` imports `build` and `train` at the top, and `combat`, `ai`, `replay` import `gather`: a module that `gather` imports must import `combat` or `gather` inside its function (#612).
- A merge conflict between two new code blocks: do not join the two sides by a script. A hunk can cut through a block (#517: the Java of the plugin did not compile). Apply your change again on main's file, then build.
