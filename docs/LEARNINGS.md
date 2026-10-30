# Learnings

Each session loads this file in each call: only lines for all runs go here, at most 3000 bytes
(`tests/test_learnings.py`, #4454). Add a line at the end and do not change other lines (`merge=union`).
A lesson that only some tickets need goes to the end of its section in `docs/PITFALLS.md`, or to the "Pitfalls"
section of its topic document: the Minecraft server, client and NBT: `docs/minecraft-versions.md`; Paper, the game
program, menus, `combat`, AoE2 wiki values: `docs/research/gameplay.md`; RCON `@e`, datapack items: `docs/datapack.md`;
records: `docs/research/replays.md`; bundles: `docs/packaging.md`; water: `docs/research/water.md`; designs: the `design` skill.

- Read the section of `docs/PITFALLS.md` before its case: claims, pushes, PRs, merge conflicts and check tickets;
  background commands and waits; downloads and blocked hosts; converter code; game program code.
- `tools/claim.py` names the run by the current local branch: run each call on the branch that pushes the ticket,
  one call per tool call and per ticket, and read the exit code before the next step (#361, #965, #4132).
- `git fetch origin main` before each `git checkout -B <branch> origin/main`: the clone can be days old (#2278).
- Wait for an `echo rc=$?` line, not for the first output; read the one result line of `pytest`, do not run it again.
  Wait for a background command by the task ID of its own result (#1243, #2510, #2342).
- The auto mode denies the close of an issue: comment the evidence, then add the label `close` (#1740).
- Automerge takes the first "close #N" (also "fix", "resolve") in a PR body as the ticket: never write those words
  before another issue number (#984).
- A test that patches a data table of a civilization key (`civs.BY_KEY`) must patch the plain `civs` too: `game/monk.py` imports it by its plain name, so a patch of `game.civs` alone changes nothing (#4447, as `tests/test_techs_saxons.py`).
