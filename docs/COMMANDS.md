# More commands

The tools that few tickets need. `CLAUDE.md` has the common commands: each call of each run reads it again, so
these rows are here (2026-10-29).

| Task | Command |
|---|---|
| Install | `python3 -m pip install -r requirements-dev.txt` (the setup script and the SessionStart hook do it; a `pip` on the PATH can be another Python) |
| Test scenarios | `python3 tools/scenarios.py NAME OUT.aoe2scenario`: `tiny`, `gallery`, `stress`, `buildings`, `units`, `village`, `facing`, `walls`, `river` (raised river with dock, bridge, boats), `river_town`, `four_civs`, `battle`, `triggers` (timer, area, create and remove triggers; count with `tools/triggers.py FILE...`), `large` (480 × 480 tiles, #690), `owner_loop` (the play-test map of the `human` skill, #1674), `layers` (terrain layers, #3690), `moods` (the village with `--mood NIGHT`, #1598), `gaia` (Gaia units that join a player, #5107) |
| Coverage of AoE2 types | `python3 tools/coverage.py OUT.md` (designs, mappings, fallbacks). Do not commit `docs/coverage.md`: CI on main does it, and `tools/feature_table.py` for `docs/DESIGN.md` |
| Agent system tools | `health.py`, `operator_check.py`, `feedback.py`, `tokens.py`, `usage.py`, `dashboard.py`, `release.py`: `framework/docs/SYSTEM.md`, "Tools of the system" |
| Game program options | `python3 game/run.py OUTWorld`: `--server vanilla` (Mojang's server), `--bench N` (commands per second), `--play` (gather resources), `--cheats` (the AoE2 cheat codes in the chat), `--replay [--speed N]` (replay a recorded game) |
| In-game screenshot options | `tools/mc_shot.py`: `--at X Y Z --look YAW PITCH`, `--more X,Y,Z,YAW,PITCH`, `--player` (adventure mode; a spectator sees invisible mobs); `mc_shot.Client`: a player on the Paper server that clicks menus |
| Unread random map commands | `python3 tools/rms_survey.py DIR` (Markdown: each `*.rms` of a folder with its warnings, and the warnings with their map counts) |
| AI script examples | `python3 tools/airef_probe.py [FILE]` (each example of the AoE2 AI Scripting Encyclopedia on a bot: the crashes and the grouped "unknown" warnings; no FILE: `commands.js` is downloaded to `out/airef/`, #5192) |
| Gather timing | `python3 tools/measure_gather.py` (server, no client: walk, chop and trip times next to AoE2; `--read F.jsonl` reads a `game/run.py --play --log` file) |
| Replay drift | `python3 tools/replay_drift.py samples/de-64.3.aoe2record --speed 4 --until 10:00 --log F.jsonl` (Paper, no client: distance of each unit to its replay position, stuck, stray and dead units per kind; `--read F.jsonl`, #813) |
| Replay shots | `python3 tools/replay_shot.py samples/de-trigger-test.aoe2record out/t.png --at-time 0:11 --at-time 0:31 [--view X,Y,Z,YAW,PITCH]` (real client in a live replay: one PNG per game time, `out/t_0m11s.png`, #5273) |
| Convert a match | `python3 aoe2mc.py --match GAME:PROFILE OUTWorld` (downloads the record into `out/records/` once; `python3 tools/record_api.py download GAME PROFILE DIR` writes only the `.aoe2record`, #4484) |
| Idle villager causes | `python3 tools/idle_split.py OUTWorld/aoe2mc.json` (offline replay of a converted record, no server, about 2 min: the idle time of each player split by the last record event of each villager; `--unit ID,ID --from MM:SS --to MM:SS` traces units, #4063) |
| Server profile | `python3 tools/server_profile.py [--seconds 60]` (next to a running Paper server: the top methods of the server thread, own and inclusive, Java Flight Recorder; `replay_drift.py --profile MM:SS-MM:SS`, #3336) |
| Conversion cost | `python3 tools/measure_convert.py IN.aoe2scenario` (seconds and peak memory of each phase; `docs/research/large-maps.md`) |
| Unit count cost | `python3 tools/measure_units.py [--units 200,500,1000]` (Paper, no client: RCON commands per second and `/tick query` with many units that walk with `aoe moveto`, #943) |
| Datapack cost | `python3 tools/tick_cost.py` (server, no client: `/tick query` with and without `datapacks/aoe2mc`; `--world W`, `--ambience full`) |
| Minecraft data | `python3 tools/mc_check.py --reports VERSION` (exact, from Mojang) or `tools/fetch_mcdata.py VERSION` writes `tools/mcdata/VERSION.json` |
| Block colors | `python3 tools/fetch_colors.py VERSION` writes `tools/mcdata/colors-VERSION.json` (for `render.py`) |
| Compare with the game data | `python3 tools/dat_compare.py [PATH/empires2_x2_p1.dat]` (local, AoE2 DE installed, `pip install genieutils-py`; default: the Steam path on macOS; one line for each value of `game/data` that differs from the `.dat`, exit 1; no `.dat`: exit 2, #5245) |
