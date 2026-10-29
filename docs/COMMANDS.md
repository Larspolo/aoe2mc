# More commands

The tools that few tickets need. `CLAUDE.md` has the common commands: each call of each run reads it again, so
these rows are here (2026-10-29).

| Task | Command |
|---|---|
| Unread random map commands | `python3 tools/rms_survey.py DIR` (Markdown: each `*.rms` of a folder with its warnings, and the warnings with their map counts) |
| Gather timing | `python3 tools/measure_gather.py` (server, no client: walk, chop and trip times next to AoE2; `--read F.jsonl` reads a `game/run.py --play --log` file) |
| Replay drift | `python3 tools/replay_drift.py samples/de-64.3.aoe2record --speed 4 --until 10:00 --log F.jsonl` (Paper, no client: distance of each unit to its replay position, stuck, stray and dead units per kind; `--read F.jsonl`, #813) |
| Server profile | `python3 tools/server_profile.py [--seconds 60]` (next to a running Paper server: the top methods of the server thread, own and inclusive, Java Flight Recorder; `replay_drift.py --profile MM:SS-MM:SS`, #3336) |
| Conversion cost | `python3 tools/measure_convert.py IN.aoe2scenario` (seconds and peak memory of each phase; `docs/research/large-maps.md`) |
| Unit count cost | `python3 tools/measure_units.py [--units 200,500,1000]` (Paper, no client: RCON commands per second and `/tick query` with many units that walk with `aoe moveto`, #943) |
| Datapack cost | `python3 tools/tick_cost.py` (server, no client: `/tick query` with and without `datapacks/aoe2mc`; `--world W`, `--ambience full`) |
| Minecraft data | `python3 tools/mc_check.py --reports VERSION` (exact, from Mojang) or `tools/fetch_mcdata.py VERSION` writes `tools/mcdata/VERSION.json` |
| Block colors | `python3 tools/fetch_colors.py VERSION` writes `tools/mcdata/colors-VERSION.json` (for `render.py`) |
