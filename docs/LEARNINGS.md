# Learnings

The agent writes here what it learned the hard way. Each line must save time in a later session.
Keep this file below 80 lines: merge similar lines and remove lines that are no longer true.

## Environment

- The cloud network blocks Mojang hosts (`piston-meta.mojang.com` gives 403). GitHub raw files and PyPI work.
- `/root/.local/bin/pytest` uses another Python. Use `python3 -m pytest`.
- Java 21 is installed in the cloud container (Minecraft 1.21.x and 26.x servers need Java 21).
- GitHub in cloud sessions: `gh api repos/Larspolo/aoe2mc/...` (REST) works. GraphQL (`gh issue list`,
  `gh pr create`) and `search/...` give 403. CI job logs: only `mcp__github__get_job_logs`.
- Scheduled runs can have no MCP connector tools. The `autopilot` skill has a REST table for that case.
- The repository is private: a workflow with a `permissions:` block also needs `contents: read`, or
  `actions/checkout` fails with "Repository not found".

## Libraries

- AoE2ScenarioParser 0.9.8 can make new scenarios: `AoE2DEScenario.from_default()`, then
  `map_manager.map_size = N`, `unit_manager.add_unit(PlayerId, ID, x=, y=)`, `write_to_file(path)`.
  It prints much text: wrap calls in `contextlib.redirect_stdout(io.StringIO())`.
- In a default scenario all players have civilization RANDOM, so all buildings use the `western` set.
- PrismarineJS minecraft-data (GitHub raw) has block data up to 26.1. Its entity and biome data for 1.21.1
  come from 1.20.5. Data versions of all releases are in `data/pc/common/protocolVersions.json`
  (26.3 = 5023).

## Code

- `Columns.ground_detail` has two road passes. The second one also changes the gravel sea floor and wraps
  around the map edge with `np.roll` (brown dots on shores and at x = 0). See its ticket.
- Drawing all 243 building types for one architecture set takes about 1 s. A full gallery conversion takes
  about 30 s per set.
