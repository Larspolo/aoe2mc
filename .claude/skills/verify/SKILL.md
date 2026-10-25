---
name: verify
description: Verify a change to aoe2mc before commit. Selects the check level (lint and fast tests, slow tests, visual check of the preview image, exact block checks) from the type of change. Use before each commit and when a ticket says "verify".
---

# Verify a change

There is no Minecraft client. Use the cheapest check that proves the change. Do all levels up to the one
that the change needs. Write the result of each check in the PR body.

## Level 1 – always (about 15 s)

    ruff check .
    python3 -m pytest

## Level 2 – the change affects blocks or entities (about 60 s)

For changes in `buildings.py`, terrain, objects, units, the chunk writer or `level.dat`:

    python3 -m pytest -m slow

This converts every object type of the parser and checks all block states, biomes and entity IDs
against `tools/mcdata/1.21.1.json`.

## Level 3 – the change affects how the world looks

1. Make a scenario that shows the change. Add a function to `tools/scenarios.py` when the existing ones do
   not show it (for example a scenario with only roads, or one building type for each architecture set).
2. Convert it twice: once with the code on `origin/main` (use `git stash` or `git worktree`), once with
   your change. Use `--preview`. Put the output in the scratchpad.
3. Scale small previews up (for example 4× with `PIL.Image.resize(..., Image.NEAREST)`). Look at both images
   with the Read tool. Describe the difference in the PR body.
4. For the 3D shape use `tools/render.py`: `building NAME --arch SET OUT.png` draws one design on flat grass,
   `sheet NAME OUT.png` draws it in all architecture sets, `world WORLD X0 Z0 X1 Z1 OUT.png` draws an area of a converted world. The default view is from the
   south-east (the front). `--view sw|ne|nw` shows the other sides. Look at the PNG with the Read tool.
5. For exact checks use `tools/world_reader.py WORLD X Y Z` or `world_reader.World(path).block(x, y, z)`.
   Add a test for the exact check when the behavior must stay.

## Level 4 – only the game can show it

Load errors: `python3 tools/mc_check.py WORLD` (about 20 s, `python3 -m pytest -m mc` for the tiny world).
It loads all chunks in a headless Minecraft server and exits with 1 when the log has problem lines (for
example "Recoverable errors when loading section", unknown block names, entity or data fixer errors).
`--log FILE` keeps the full log. The server replaces a bad property value (`facing=up`) with the default and
does not log it: `mcvalid` finds those. `python3 tools/mc_check.py --reports VERSION` makes exact
`tools/mcdata/VERSION.json` from Mojang's data reports.

Examples for the game: unit facing, light, entity behavior.
For what only a person can see, make a `needs-human` ticket with: the scenario or the command that makes the
test world, and exact steps for the owner ("Open the world. Stand at X Y Z. Look north. The knight must
face you.").

## Rules

- A test must fail before a bug fix and pass after it.
- Output must stay deterministic. Two conversions of the same scenario with the same seed give the same files.
- `tests/test_golden.py` fails when the output of the tiny scenario changes. If the change is on purpose, write
  a new golden file (`AOE2MC_UPDATE_GOLDEN=1 python3 -m pytest tests/test_golden.py`), commit it and explain in
  the PR body which blocks or entities changed and why. A refactor must not change the golden file.
- If a check fails for a reason outside your change, do not hide it. Make a ticket and say so in the PR.
