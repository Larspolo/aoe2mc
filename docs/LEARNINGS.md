# Learnings

The agent writes here what it learned the hard way. Each line must save time in a later session.
Keep this file below 80 lines: merge similar lines and remove lines that are no longer true.

## Environment

- GitHub raw files, PyPI and the Mojang hosts (`piston-meta`, `piston-data`, `libraries.minecraft.net`) work.
- `/root/.local/bin/pytest` and `/usr/bin/pip` use another Python: use `python3 -m pytest`, `python3 -m pip`. "cannot import
  name '_imaging' from 'PIL'": the Debian pillow shadows it: `python3 -m pip install --ignore-installed pillow`.
- `minecraft.wiki`, `minecraft.net` and `papermc.io` are blocked. For Minecraft facts use the Mojang data reports in
  `misode/mcmeta` (GitHub raw, branch `<version>-summary`) and the real server (`docs/minecraft-versions.md`, "Method").
- Minecraft 26.3 (the default) needs Java 25: `scripts/cloud-setup.sh` or `tools/mc_check.py` (apt-get as root) installs it (#195).
  Send `stop` only after "Done (" is in `logs/latest.log`. Do not use `pkill -f server.jar`: it kills your own shell.
  A `&` job ignores SIGINT: test Ctrl-C with `Popen(..., start_new_session=True)` and `os.killpg(pid, SIGINT)` (#137).
- GitHub in cloud sessions: `gh api repos/Larspolo/aoe2mc/...` (REST) works. GraphQL (`gh issue list`, `gh pr create`),
  `search/...` and branch deletes give 403. CI job logs: only `mcp__github__get_job_logs`. A push to a new ref works,
  a non-fast-forward push fails: `tools/claim.py` uses it as a lock (#211). REST ref paths: `git/refs/heads/...`.
- Quote the heredoc tag (`<<'EOF'`) for GitHub text: `<<EOF` runs each `` `name` `` as a command. Pass paths as arguments.
- A task from `create_trigger` has no repository: set `Larspolo/aoe2mc` in the claude.ai UI. Scheduled runs use
  Sonnet 5.5 unless the task sets another model. Some sessions have no `fire_trigger` tool: skip the fan-out, report it.
- The repository is private: a workflow with a `permissions:` block also needs `contents: read`, or
  `actions/checkout` fails with "Repository not found". The `pulls` API needs `pull-requests: read` (else 403).
  A new `workflow_dispatch` workflow runs only after the merge to `main` (`/actions/workflows/F.yml/dispatches`, #207).
- Minecraft server: a bad property value (`facing=up`) loads silently as the default state. An unknown block gives
  "Recoverable errors when loading section". A missing `level.dat` compound gives "key missing: <name>" (#60).
  An unknown block entity id gives "Skipping block entity with invalid type": 26.3 has no `bed` (#249).
- Minecraft client (#178, #179): `tools/mc_shot.py` runs it in `Xvfb` (no window, offline, no sound). 1.21.1: Mesa OpenGL.
  26.3 finds no GLX visual in Xvfb: it needs `mesa-vulkan-drivers` (lavapipe) and Java 25, and a placeholder for the
  title panorama (the asset host is blocked). Hidden chat (`chatVisibility:2`) stops the chat lines in the log too.
- AoE2 wiki: HTML pages give 403 (Cloudflare). Use `tools/refimage.py` (MediaWiki API, own `User-Agent`). Page text:
  `api.php?action=parse&page=Title&prop=wikitext&format=json&formatversion=2`.
- AoE2 recorded games: the record hosts (`aoe.ms`, `data.aoe2companion.com`, `www.aoe2insights.com`) are blocked.
  `samples/de-64.3.aoe2record` is an `mgz` test record (MIT, #134; more in `happyleavesaoc/aoc-mgz/master/tests/recs/`):
  `mgz.model.parse_match(f).map.tiles` gives terrain and elevation of a real DE map. Install `mgz` after
  `python3 -m pip install --ignore-installed setuptools` (the Debian setuptools cannot build it).
  A record has each town center 4 times (IDs 109 and the annex parts 618–620): `read_record` skips them (#139).

## Libraries

- AoE2ScenarioParser 0.9.8 makes new scenarios (`tools/scenarios.py`: `new_scenario`, `add_unit`, `save`). It prints much
  text (`redirect_stdout`), default players are RANDOM (`western`), and `write_to_file` writes the output file name into
  the file: for the same bytes use `scenarios.save(..., name)` (#204).
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
  gate along tile x): `plan_walls` uses the walls next to the gate. `--orientation` turns the tile grid (`turn_map`)
  and each building canvas (`buildings.turn`); gates, walls and bridges follow their neighbours.
- Golden test: change the house chimney of the tiny scenario to see it fail. `columns()` in `tests/test_terrain.py`
  makes `Columns` from a terrain array. Maps of one size draw the same random numbers: compare them per block.
- `place_objects` without a scenario: call it with one object dict (`kind`, `name`, `player`, `x`, `y`,
  `rotation`, `hero`, `garrisoned`) on a 16 × 16 `Columns`. With `sys.settrace` this shows which branch each
  `OtherInfo` name takes (#6). Buildings (also `FISH_TRAP`, docks) need `kind="B"`, else nothing is placed.
  `build_chunk` returns `(nbt, vol)`: test exact blocks of a chunk with `vol` (#19).
- `aoe2mc.py` reads `tools/mcdata/1.21.1.json` at import (#19). The package ships it as `tools.mcdata`
  (`pyproject.toml`). A new runtime data file must go into the package data too (test: `pip install .` in a venv).
- `terrain_style`: an earlier rule wins (#5). AoE2 has no water level: real maps have all water at elevation 0 (#164).
- `.gitattributes` merges `docs/DESIGN.md` with `union`: a local merge keeps the new table lines of both sides; look for one
  line in two versions and keep one. GitHub ignores `union` (the PR is "dirty", #210). Not for text that runs rewrite (#174).
- PRs do not change `docs/coverage.md` or `MAX` in `tests/test_coverage.py`: the `coverage.yml` workflow updates them on
  main (#233). A conflict there (old PR): take main's side. Check `mergeable_state` after the push: a PR is "dirty"
  when main moved. `automerge.yml` merges green agent PRs (#232).
- Block IDs in `B` depend on earlier tests or conversions: draw random numbers per block in state-name order, not
  ID order (#44). A test that passes alone but fails in the full suite often has this cause.
- An invalid item in a block entity can vanish without a log line. `tools/mc_check.py W --keep DIR` keeps the world
  that the server saved: read it with `tools/world_reader.py` (1.21.1 saves the loaded chunks again, 26.3 can skip them) (#27).
  26.3 saves a default state as the bare name and puts the properties in another order: normalize before you compare (#189).
- New entity NBT: convert a map with one unit per type (`add_unit` in a loop) and run `tools/mc_check.py` (1 min).
- `vary()` picks a `ROOF_ALT` material per variant: count blocks with `render.building_blocks(NAME, arch, variant=v)` (#146).
