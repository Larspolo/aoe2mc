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
  `Content-Type: application/json`, else 415 (#345). GitHub text: quote the heredoc tag (`<<'EOF'`), `<<EOF` runs `` `name` ``. The clone is shallow: `git fetch --unshallow origin` before a scan of the history (#367).
- Pitfalls of the Minecraft server, client and NBT (silent defaults, dropped tags): `docs/minecraft-versions.md`; of Paper
  and the game program: `docs/research/gameplay.md`; of RCON `@e`: `docs/datapack.md`; of records (`mgz`, test records):
  `docs/research/replays.md`; of designs (cylinders, furniture, renders, shelf items): the `design` skill ("Pitfalls").
- `tools/claim.py` names the run by the local branch (`who()`): beat only from the session branch, never in parallel (#361).
  Run `claim.py N --guard` alone and read its exit code before the push: `guard; echo g=$? && git push` pushes also after
  a failed guard (#540).
- `addopts` has `-q`: `python3 -m pytest -q` gives no "N passed" line, so wait for the exit code. Foreground `sleep` is blocked:
  `run_in_background`, then `timeout 580 bash -c 'until [ -s OUT ]; do sleep 5; done'` (#413, #514).
- `mcp__github__get_job_logs` gives HTTP 404 for the jobs of `ci.yml` (2026-10-26, #443): do not retry. Run its steps
  (`ruff`, fast, `-m slow`, `-m mc`) locally on the run's `head_sha`; main is red only when one fails there.
- `-m mc` takes about 21 minutes and needs `javac` and `xdotool` (setup version 7, #493, #638): on an older setup
  run `apt-get install -y openjdk-25-jdk-headless xdotool` first; without `xdotool` it skips `tests/test_menu_client.py`.
- AoE2ScenarioParser 0.9.8 makes new scenarios (`tools/scenarios.py`: `new_scenario`, `add_unit`, `save`). It prints much
  text (`redirect_stdout`), default players are RANDOM (`western`), `write_to_file` writes the output file name into the file
  (same bytes: `scenarios.save(..., name)`, #204), and it refuses to write over the file that it read: read a temporary copy
  (`scenarios.triggers`). No scenario in `examples/` and `samples/` has triggers: use the `triggers` scenario (#646).
- Images of a check ticket or a PR: push an orphan commit (`git mktree`, `git commit-tree`) to `refs/heads/checks/N` and
  link `https://raw.githubusercontent.com/Larspolo/aoe2mc/checks/N/NAME.png` (#614). A second check: build the tree from
  the old tree and the new files (`git ls-tree OLD` piped into `git mktree`), else the old image links break (#718).
- Same output of a conversion: compare two worlds with `tools/world_diff.py A B`. `diff -r` and `cmp` always differ: the .mca time tables, gzip headers and `LastPlayed` hold the time (#702).
- The auto mode classifier can deny `gh api .../issues/N -X PATCH -f state=closed` (closing a finished epic: "External System Writes"). Do not send the same close through another tool: add `needs-human` to the epic and a comment with the evidence for `@Larspolo` (#862).
- `S=dir && cmd1 & cmd2 $S/x`: the `&` puts the whole `S=... && cmd1` list in a background subshell, so `cmd2` sees an empty `S` and writes to `/x` (#865). Set the variable on its own line first.
- `tools/claim.py` fetches, so it overwrites `FETCH_HEAD`: fetch a `checks/N` ref into a named ref (`git fetch origin +refs/heads/checks/N:refs/remotes/origin/checks/N`) before you build its next commit, else the push is non-fast-forward.
- The auto mode denies an edit of a skill that closes epics through a PR because a close was denied ("Instruction Poisoning", #971): it is a way around the denial. Do not try another way: ask the owner on the ticket.
- Automerge takes the first "close #N" (also "fix", "resolve") anywhere in the PR body as the ticket, also in "does not close #N": a ticket with `needs-human` then stops the merge (#984). Do not write those words before another issue number.
- The auto mode also denies the commit of the no-code PR of autopilot step 5 that closes an epic ("Auto-Mode Bypass", 2026-10-26, #842): add `needs-human` and a comment with the evidence for each criterion on the epic, and continue.
- A check ticket that waits for a fix: `git fetch origin main && git checkout -B <branch> origin/main` just before the level-4 run, and name the commit in the result. A run that checked out main earlier checks the old code (#964: 10 minutes lost).
- A wait loop on an output file (`until grep -q ... OUT`) of a second run reads the old file of the first run: `rm -f OUT` before the new run, or use a new name (#738).
- Run `tools/claim.py N` in its own tool call and read its exit code before the label and the "Started by" comment: in parallel tool calls they run also on exit 1, on a ticket of another run (#965).
- AoE2 values (hit points, attack, `ROF`, armor) of a unit or building: the MediaWiki API `api.php?action=parse&page=NAME&prop=wikitext&format=json&redirects=1` (User-Agent of `tools/refimage.py`) gives the infobox fields. A name of several games is a disambiguation page: use `Watch_Tower_(Age_of_Empires_II)` (#1112).

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
- `aoe2mc.json`: object kind is `"unit"`; `"id"` is the AoE2 type constant, the object ID of a record is `"ref"` (#408).
  The "ground" of a blocked footprint is the barrier top: take the free cells of `Map.around()` (#307, #391). Stump names:
  `STUMP`, `*_STUMP`. The `buildings` scenario: building i of `BuildingInfo` is near tile (4 + i % 40 × 7, 4 + i // 40 × 7).
- Parallel sibling tickets: before you add a helper or a tool option, `git fetch origin main` and grep for it (two runs
  added a `furnish()`; the second broke main, #263).
- "units in a block": `AOE2MC_DEBUG=1` names the block; list the `aoe2mc.json` objects with a `tile` near the unit to
  find its source (#415: a `PLANT_SHRUB` on the same block, not the tree that the ticket named).
- A gate footprint is not in `cols.blocked` (units walk through the passage): `place_building` blocks only the columns with a solid block at head height (#577). Reproduce "units in a block" of a campaign with `tests/test_scx.py` `build()` and random units on the wall line. With a step under a gate, the foundation lifts the passage floor: `buildings.FLOORS` holds the stand height (#773); a slope: `elevation` in `build()` (`tests/test_scx_walls.py`).
- A change to the blocks of an object: also run the `-m mc` tests of the files that name it (`grep -l NAME tests/`): the fast suite skips them, and #590 broke `test_villager_forages_on_a_server` (fixed in #602).
- A merge conflict between two new code blocks: do not join the two sides by a script. A hunk can cut through a block (#517: the Java of the plugin did not compile). Apply your change again on main's file, then build.
- The full test suite has `tools/` and `game/` on `sys.path`: a new `game/X.py` with the name of a `tools/X.py` (`health`) imports the wrong module there, but its own test file passes alone (#659). Check `ls tools/X.py` first.
- `[f"...{o['id']}"] * ("id" in o)` evaluates the f-string also when the factor is 0 (KeyError): use `o.get('id')` in it (#681).
- `place_objects` tests `"FLAG" in name` before `units.invisible(name)`: an invisible object named `*FLAG*` becomes a flag. Give it a name of `units.INVISIBLE` without `FLAG` (`INVISIBLE_OBJECT`, #772).
- The free space of a design is `-1` (unset) or `air`: an open hall (the western `TOWN_CENTER`) has no `air` cell inside. `buildings.rooms()` takes both, the `air` cells first (#807).

- A new player gets an item through the datapack pulse (`item replace entity @s weapon.offhand`, a tag against
  repeats), not through `Data.Player` of `level.dat`: the 26.3 client ignored a `Player` tag that the converter
  wrote (#966). The datapack also works on a server, where `level.dat` has no player.
- `tests/test_menu.py` `test_gather_reads_the_menu_clicks` builds a bare `Gather.__new__` with only the attributes that `clicks()` uses: a new attribute that `clicks()` reads must go there too, else the full suite fails with AttributeError (#992).
- `python3 -m pytest -m mc tests/A.py tests/B.py` can stop with "No module named 'bossbar'" (a test file imports a `game/` module by its bare name): run it with `PYTHONPATH=game:tools:.` (#1045).
- In tests, `from game import build` and the bare `build` that `game/*.py` import are two module objects: a table that `train.py` changes at import (`build.AGE |= ...`, #1082) is only in the bare one. Read it through the importer (`train.build`).
- A ticket can name a new test file that exists already (`tests/test_replay_jump_gather.py`, #1147): run `ls` on the name before you write it, else `cat >` overwrites the old tests.
- AoE2 terrain 1 is `WATER_SHALLOW` (the normal DE water, rmap `WATER`), terrain 4 is `SHALLOWS` (walkable): `terrain_style` matches "SHALLOW" in both and makes both 1 block deep until #1198. Check a river with `world_reader.py --section`, not the preview (no depth shade).
- An AoE2 value in a ticket can be wrong (#1113 said an empty town center shoots 1 arrow; the wiki infobox says 0, #1201): check each AoE2 number of a ticket with the MediaWiki API before the code.
