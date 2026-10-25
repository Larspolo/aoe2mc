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
4. For exact checks use `tools/world_reader.py WORLD X Y Z` or `world_reader.World(path).block(x, y, z)`.
   Add a test for the exact check when the behavior must stay.

## Level 4 – only the game can show it

Examples: unit facing, light, entity behavior. Load errors: use `tools/mc_check.py` when it exists (#13).
For what only a person can see, make a `needs-human` ticket with: the scenario or the command that makes the
test world, and exact steps for the owner ("Open the world. Stand at X Y Z. Look north. The knight must
face you.").

## Rules

- A test must fail before a bug fix and pass after it.
- Output must stay deterministic. Two conversions of the same scenario with the same seed give the same files.
- If a check fails for a reason outside your change, do not hide it. Make a ticket and say so in the PR.
