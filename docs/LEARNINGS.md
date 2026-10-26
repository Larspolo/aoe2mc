# Learnings

The agent writes here what it learned the hard way. Each line must save time in a later session.
Ticket runs: add new lines at the end of a section and do not change other lines (`merge=union` in `.gitattributes`
keeps the lines of both sides). A pitfall of one topic (server, Paper, records, a design) goes into the "Pitfalls" section
of its document (named below; add at its end, do not change other lines: `merge=union` too): this file loads into each run. The `improve` skill merges lines and keeps it below 80 lines.

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
  `Content-Type: application/json`, else 415 (#345). GitHub text: quote the heredoc tag (`<<'EOF'`), `<<EOF` runs `` `name` ``.
- Pitfalls of the Minecraft server, client and NBT (silent defaults, dropped tags): `docs/minecraft-versions.md`; of Paper
  and the game program: `docs/research/gameplay.md`; of RCON `@e`: `docs/datapack.md`; of records (`mgz`, test records):
  `docs/research/replays.md`; of designs (cylinders, furniture, renders, shelf items): the `design` skill ("Pitfalls").
- `tools/claim.py` names the run by the local branch (`who()`): beat only from the session branch, never in parallel (#361).
  Run `claim.py N --guard` alone and read its exit code before the push: `guard; echo g=$? && git push` pushes also after
  a failed guard (#540).
- The cloud clone is shallow: `git fetch --unshallow origin` before a scan of the history (#367).
- A run of the scheduled task has only `subscribe_pr_activity` and `unsubscribe_pr_activity` of `claude-code-remote`:
  no `fire_trigger`, `send_later` or `list_triggers` (checked 2026-10-26, #566). The pacer session starts the runs.
- Quota usage: `claude -p ... --output-format stream-json --verbose` prints a `rate_limit_event` with
  `unifiedWindows.five_hour/seven_day.utilization` and `resetsAt` (`tools/usage.py`). A `statusLine` does not run in cloud sessions.
- `pyproject.toml` `addopts` has `-q`: `python3 -m pytest -q` gives `-qq`, without the "N passed" line. Wait for the
  exit code, not for "passed" in the output; foreground `sleep` is blocked: use `run_in_background` and wait with
  `timeout 580 bash -c 'until [ -s OUT ]; do sleep 5; done'` (#413, #514).
- `mcp__github__get_job_logs` gives HTTP 404 for the jobs of `ci.yml` (2026-10-26, #443): do not retry. Run its steps
  (`ruff`, fast, `-m slow`, `-m mc`) locally on the run's `head_sha`; main is red only when one fails there.
- `-m mc` takes about 21 minutes and needs `javac` (setup version 6, #493): when `/etc/aoe2mc-setup-version` is below 6,
  run `apt-get install -y openjdk-25-jdk-headless` first (1 min, #536).
- AoE2ScenarioParser 0.9.8 makes new scenarios (`tools/scenarios.py`: `new_scenario`, `add_unit`, `save`). It prints much
  text (`redirect_stdout`), default players are RANDOM (`western`), and `write_to_file` writes the output file name into
  the file: for the same bytes use `scenarios.save(..., name)` (#204).
- Images of a check ticket (no PR): push an orphan commit (`git mktree`, `git commit-tree`) to `refs/heads/checks/N` and
  link `https://raw.githubusercontent.com/Larspolo/aoe2mc/checks/N/NAME.png` in the comment (#614).
- AoE2ScenarioParser refuses to write over the file that it read ("Overwriting the source scenario file"): read a
  temporary copy (`scenarios.triggers`). No scenario in `examples/` and `samples/` has triggers: use the `triggers` scenario (#646).
- A wait loop with a fake clock (`now += s`) runs forever when the wait is about 1e-15: `now + 1e-15 == now`. Break on `wait <= 1e-6`, not `<= 0` (#685).
- Screenshots of a game check: join `mc_shot.Client(game.game_port, game.version)` to the running `run.Game`, `gamemode spectator aoe2mc`, then `tp aoe2mc X Y Z facing entity <uuid>` and `client.shot()`: no saved world, no copy of the `.dat` files. The server log is `game.folder/logs/latest.log`: read it before the `with` ends (#603).
- Same output of a conversion: compare two worlds with `tools/world_diff.py A B`. `diff -r` and `cmp` always differ: the .mca time tables, gzip headers and `LastPlayed` hold the time (#702).
- `-m mc` skips `tests/test_menu_client.py` (a real client) without `xdotool` (setup below v7, #638): `apt-get install -y xdotool` first; the skip hid a broken handler there until #706.
- `run.Game(world)` plays on the world folder itself (`--universe`, no copy): the game saves its changes there. Copy the converted world for each check run, else the second run starts with felled trees and empty bushes (#718). A live replay at `--speed 8` leaves the real villagers far behind the replay positions: check at speed 4.
- `mc_shot.Client` hides the chat (`chatScale` 0): pass `chat=True` for an image of a message. The client log (`client.text()`, `[CHAT]`) has each chat line; the server log has no `tellraw` text. `Gather.setup` reads no stock from the sidebar: set `scoreboard players set Food aoe_res N` with `g.stock` (#780).
- `execute if entity @e[...]` on 26.3 answers "Test passed. Count: N" (a capital C, a full stop); the `FakeServer` of `tests/test_gather.py` writes "Test passed, count: 1". Match `Count: (\d+)` and check a new answer on a real server (#787).
- The auto mode classifier can deny `gh api .../issues/N -X PATCH -f state=closed` (closing a finished epic: "External System Writes"). Do not send the same close through another tool: list the epic and its evidence on the status issue (#766 run).

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
  and `MAX` in `tests/test_coverage.py` (`coverage.yml`, #233, #234). A conflict there: take main's side. `docs/coverage.md`
  can be stale (#460): for the real fallbacks run `python3 tools/coverage.py OUT.md` into the scratchpad (#500).
- Block IDs in `B` depend on earlier tests: draw random numbers in state-name order, not ID order (a cause of full-suite-only failures, #44).
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
- A gate footprint is not in `cols.blocked` (units walk through the passage): `place_building` blocks only the columns with a solid block at head height (#577). Reproduce "units in a block" of a campaign with `tests/test_scx.py` `build()` and random units on the wall line.
- A change to the blocks of an object: also run the `-m mc` tests of the files that name it (`grep -l NAME tests/`): the fast suite skips them, and #590 broke `test_villager_forages_on_a_server` (fixed in #602).
- A merge conflict between two new code blocks: do not join the two sides by a script. A hunk can cut through a block (#517: the Java of the plugin did not compile). Apply your change again on main's file, then build.
- `game/build.py` has a function `menu()` (the chat text of /trigger): it imports `game/menu.py` as `chest` (#621).
- The full test suite has `tools/` and `game/` on `sys.path`: a new `game/X.py` with the name of a `tools/X.py` (`health`) imports the wrong module there, but its own test file passes alone (#659). Check `ls tools/X.py` first.
- A train test (`game/train.py`) needs an own `TOWN_CENTER` or `HOUSE`: without them the population limit is 0 and `tick()` spawns nothing (#654).
- `[f"...{o['id']}"] * ("id" in o)` evaluates the f-string also when the factor is 0 (KeyError): use `o.get('id')` in it (#681).
- `game/combat.py` `stats()`: a name that is not a `STATS` key gets `DEFAULT` (40 hit points) without a warning. The units of `aoe2mc.json` have names like `VILLAGER_MALE`: compare with `units.classify` names, not the table keys (#655).
- A new item of a building menu (`train.show()`) changes the exact menu strings in 5 test files (`grep -n "aoe menu Steve\|endswith(\"queue" tests/`): add it as a constant next to `FEUDAL` and `RALLY` in `tests/test_train_menu.py` (#672, #707).
- `game/replay.py` uses the resource looks of `gather.Gather` through `Replay.crew` (`Gather.__new__` with `map`, `trunks`, `bushes` and a `command` attribute): no copy of the look code (#631).
- `place_objects` tests `"FLAG" in name` before `units.invisible(name)`: an invisible object named `*FLAG*` becomes a flag. Give it a name of `units.INVISIBLE` without `FLAG` (`INVISIBLE_OBJECT`, #772).
- Before #773 the ship and bridge paths of `entity_chunk` counted "units in a block" without a debug line. With a step under a gate, the foundation lifts the passage floor: `buildings.FLOORS` holds the stand height. Reproduce a slope with `elevation` in `tests/test_scx.py` `build()` (`tests/test_scx_walls.py`).
- `test_gather_attack.click` puts the eye at the ground height (y 64): its ray cannot hit the ground, so `pick_ground` and `build.pick` give the wrong cell. For a ground click put the eye 2 blocks up (`tests/test_order_marker.py` `look`, #796).
- `Replay.run` gives `control["time"]` as a float (ms): a test of a poll action with an int time hides a format error like `:02d` (#803). Test with a float time, or with `Replay.run` and the `Clock` fake of `tests/test_replay_control.py`.
