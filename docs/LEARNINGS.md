# Learnings

The agent writes here what it learned the hard way. Each line must save time in a later session.
Keep this file below 80 lines: merge similar lines and remove lines that are no longer true.

## Environment

- GitHub raw files, PyPI and the Mojang hosts (`piston-meta`, `piston-data`, `libraries.minecraft.net`) work.
- `/root/.local/bin/pytest` and `/usr/bin/pip` use another Python. Use `python3 -m pytest` and `python3 -m pip`.
  Symptom: "cannot import name '_imaging' from 'PIL'" in the end-to-end tests. If it stays after the install,
  the old Debian pillow shadows it: `python3 -m pip install --ignore-installed pillow`.
- Java 21 is installed in the cloud container. Minecraft 1.21.1 needs Java 21, 26.3 needs Java 25
  (`javaVersion.majorVersion` in the version JSON). The Mojang hosts are allowed since #12.
- GitHub in cloud sessions: `gh api repos/Larspolo/aoe2mc/...` (REST) works. GraphQL (`gh issue list`,
  `gh pr create`) and `search/...` give 403. CI job logs: only `mcp__github__get_job_logs`.
- Scheduled runs can have no MCP connector tools. The `autopilot` skill has a REST table for that case.
- A scheduled task that `create_trigger` made has no repository: its sessions have no `add_repo` tool and
  cannot clone ("GitHub access to this repository is not enabled for this session"). The scheduled task
  must have `Larspolo/aoe2mc` as its repository (set it in the claude.ai UI). Scheduled runs use Sonnet 5.5
  unless the task sets another model.
- The repository is private: a workflow with a `permissions:` block also needs `contents: read`, or
  `actions/checkout` fails with "Repository not found".

- AoE2 wiki: HTML pages give a Cloudflare challenge (403). The MediaWiki API works: `ageofempires.fandom.com/
  api.php?action=query&titles=File:Castle_aoe2DE.png&prop=imageinfo&iiprop=url&format=json` gives the image URL
  on `static.wikia.nocookie.net` (WebP).

## Libraries

- AoE2ScenarioParser 0.9.8 can make new scenarios: `AoE2DEScenario.from_default()`, then
  `map_manager.map_size = N`, `unit_manager.add_unit(PlayerId, ID, x=, y=)`, `write_to_file(path)`.
  It prints much text: wrap calls in `contextlib.redirect_stdout(io.StringIO())`.
- In a default scenario all players have civilization RANDOM, so all buildings use the `western` set.
- PrismarineJS minecraft-data (GitHub raw) has block data up to 26.1. Its entity and biome data for 1.21.1
  come from 1.20.5. Data versions of all releases are in `data/pc/common/protocolVersions.json`
  (26.3 = 5023).

## Code

- The tiny scenario has only a town center, a house and a barracks. To see the golden test fail, change a
  block that these designs draw last (for example the house chimney).

- Test terrain code without a scenario: `columns()` in `tests/test_terrain.py` makes `aoe2mc.Columns` from a
  small terrain array. Maps of the same size draw the same random numbers, so two maps can be compared per block.
- `terrain_style` checks names in sequence: an earlier rule wins (`ROAD_GRAVEL` matched `GRAVEL` until #5).
- Drawing all 243 building types for one architecture set takes about 1 s. A full gallery conversion takes
  about 30 s per set.
- Block IDs in `B` depend on what was registered before (earlier tests or conversions). Code that draws random
  numbers per block ID must go in state-name order, not ID order (see #44). A test that passes alone but
  fails in the full suite often has this cause.
