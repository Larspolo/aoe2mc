---
name: verify
description: Verify a change to aoe2mc before commit. Selects the check level (lint and fast tests, slow tests, visual check of the preview image, exact block checks) from the type of change. Use before each commit and when a ticket says "verify".
---

# Verify a change

Use the cheapest check that proves the change. Do all levels up to the one that the change needs.
The Minecraft client runs only headless: it makes screenshots (level 5). Write the result of each check in the PR body.

## Level 1 – always (a few seconds to a minute)

    ruff check .
    python3 -m pytest tests/test_a.py tests/test_b.py

Never run the full fast suite (`python3 -m pytest` with no test file, owner #4187): the quick CI runs it on each push,
and Automerge waits for it. Run `ruff check .`, the test files of the change, and the test files of the changed code
(`grep -l MODULE tests/*.py`; `framework/tools/ship_pr.py` runs this set by itself). Add other test files when you think that
the change can break them. Use `-n auto` (`pytest-xdist`, #2415) only for more than about 8 files: a few files start
faster without it, and do not use it for `-m mc` (each test starts a server). Before #4187, the full runs took 44 %
of the run minutes (408 of 920 minutes in 100 merged PRs).
A red CI after the push: read the failed tests of the job (`mcp__github__get_job_logs`), run those files, fix, push.
The PR body names what a later run needs to continue (the changed places, the tests that you ran, what is left).

## Level 2 – the change affects blocks or entities (about 60 s)

For changes in `buildings.py`, terrain, objects, units, the chunk writer or `level.dat`:

    python3 -m pytest -m slow

This converts every object type of the parser and checks all block states, biomes and entity IDs
against `tools/mcdata/<output version>.json` (26.3 by default).

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
   An opening (gate, arch, the space under a bridge) can look closed from outside: the inner faces fill it.
   Cut through it: start the `world` area inside the object (for example X0 = the middle of the gate).
5. For exact checks use `tools/world_reader.py WORLD X Y Z` or `world_reader.World(path).block(x, y, z)`.
   Add a test for the exact check when the behavior must stay.

## Level 4 – only the game can show it

Load errors: `python3 tools/mc_check.py WORLD` (about 20 s, `python3 -m pytest -m mc` for the tiny world).
It loads all chunks in a headless Minecraft server and exits with 1 when the log has problem lines (for
example "Recoverable errors when loading section", unknown block names, entity or data fixer errors).
`--log FILE` keeps the full log. The server replaces a bad property value (`facing=up`) with the default and
does not log it: `mcvalid` finds those. `python3 tools/mc_check.py --reports VERSION` makes exact
`tools/mcdata/VERSION.json` from Mojang's data reports.

Check tools of the game program (#5461): a change of the code that a tool checks runs the tool before the push. Do not
leave it to a later check ticket: 5 fixes of the replay info line merged with unit tests only, and each next check
ticket found the next fault (#5312, #5313, #5413, #5440, #5443).

| The change | The check (Paper and the real client) |
|---|---|
| The replay info line, `Replay.eye`, the camera, `aoe batch` | `python3 tools/replay_shot.py samples/de-64.3.aoe2record out/c.png --at-time 1:00 --camera player --info out/c.json` (exit 1: no unit line) |
| The replay views, the trigger titles | `tools/replay_shot.py` (screenshots at game times) |
| The tutorial (`run.py --play --tutorial`) | `tools/tutorial_check.py` |
| The game of a person against the bot | `tools/play_check.py` (no client) |

## Level 5 – in-game screenshot (before you ask the owner)

Use it when only the Minecraft client shows the answer: unit facing, map orientation, how a building looks
in the game (light, textures, connected fences and panes), what the player sees at the spawn.

    python3 tools/mc_shot.py WORLD OUT.png                                  # the spawn view
    python3 tools/mc_shot.py WORLD OUT.png --at X Y Z --look YAW PITCH --more X,Y,Z,YAW,PITCH

- The 26.3 client runs with Mesa Vulkan in Xvfb (`mesa-vulkan-drivers`, Java 25: `scripts/cloud-setup.sh`), about
  25 s per world.
- Yaw: 0 = south, 90 = west, 180 = north, -90 = east. Pitch: positive looks down (90 = top view).
- Repeat `--more` for each extra view (OUT_2.png, OUT_3.png ...). The world loads once for all views.
- A player on the Paper server of the game program (#627): `mc_shot.Client(game.game_port, game.version)` joins the
  client as "aoe2mc" (`wait_join()`), `shot(PATH)`, `click(*client.slot(i, rows))` clicks a chest menu, `key(NAME)`
  (xdotool), `pick(g, UUID or rect)` aims and right clicks a unit or building (#2963). Example: `tests/test_menu_client.py`. Join takes about 40 s after the server start.
- Use the shared start of a check script (#3831), do not write your own versions: `Client(..., world=WORLD)` deletes
  the saved files of the player (a dead player starts alive), `place(game, X, Y, Z)` puts the player on a 3 × 3
  platform and waits 15 s for the chunks, `Client.health(game, UUID or tag)` reads the `Health` of a mob.
  Example: `tests/test_mc_shot_start.py`.
- Before the first `key()` or `xdo()` of a client, call `client.wait_loaded(game)`: `wait_join()` returns when the server
  lists the player, but the client shows "Loading terrain" for about 7 s more and drops the keys (#3889).
- Direction of a mob: look at it from the side, 8–10 blocks away, pitch 10. A top view does not show the head.
- Look at each image with the Read tool and describe it in the PR body. Comment the result on the ticket.

The agent judges the look and the clicks itself (owner, 2026-10-27, #1707: 59 check runs in 24 h used 11 % of the run
minutes, and 28 of them ended with `needs-human`). Real input: `mc_shot.Client` clicks the menus and presses the keys
of a real client. The look: put the `mc_shot.py` image next to the AoE2 reference image (`tools/refimage.py`, as the
`design` skill does), list the differences and write the verdict. A look point goes to the owner only when the agent
cannot decide, and the comment says why. Only what no tool can judge goes to the owner: sound, the feel of a control
(delay, how hard it is to aim) and "is it fun" (owner, #1159, #1707). An agent measures
times, speeds and values and reads the texts in the game (menu items, lore, chat) itself, and compares them with AoE2:
never ask the owner about them. A look question ("does X look different enough from Y?") links the image before next
to the image after, or the AoE2 image next to the Minecraft image.

Examples for the game: unit facing, light, entity behavior.
For what only a person can see, make a check ticket with: the scenario or the command that makes the
test world, and exact steps for the owner. An agent runs the check (server, simulated clicks, screenshots), comments
the results and the images, and lists the points that only a person can check (#580). Then it closes the ticket on
this evidence with the label `owner-sample`, not `needs-human` (owner decision B, #1708): the owner checks a sample of
the closed checks later (`human` skill, `framework/tools/owner_tasks.py --sample`).
A check that finds a bug does not go to the owner: make the bug tickets, add "Depends on: #bug" to the check ticket and
check again when they are closed (#668).
Example steps: ("Open the world. Stand at X Y Z. Look north. The knight must
face you.").

## Rules

- A test must fail before a bug fix and pass after it.
- A test must not fail when a data file or a configuration file changes: no literal copy of their values, texts or
  settings (owner, 2026-10-29, `docs/extend.md`). A new or changed test that uses the unit or building data:
  `python3 tools/data_shake.py TEST_FILE` must print no test (it runs the test with changed data, #5388).
- Output must stay deterministic. Two conversions of the same scenario with the same seed give the same files.
- `tests/test_golden.py` fails when the output of the tiny scenario changes. If the change is on purpose, write
  a new golden file (`AOE2MC_UPDATE_GOLDEN=1 python3 -m pytest tests/test_golden.py`), commit it and explain in
  the PR body which blocks or entities changed and why. A refactor must not change the golden file.
- If a check fails for a reason outside your change, do not hide it. Make a ticket and say so in the PR.
- Parallel tickets change the same file (`AoePlugin.java`, `game/gather.py`, `game/replay.py`): before the last check
  round, `git fetch origin main` and `git diff --stat HEAD...origin/main -- <the files of your diff>`. When main changed
  one of them, merge `origin/main` and also run the `-m mc` tests that the merged commits added or changed
  (`git diff --name-only ORIG_HEAD HEAD -- tests/`). Your own tests do not see the new behavior: #770 (attack back)
  broke `test_mounted_death.py` of #732, which merged 20 minutes before; the night run finds it only hours later.
