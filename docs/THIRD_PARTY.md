# Files from elsewhere

This list has each file or group of files in the repository (and in its history) that does not come only from
this project. Check it before the repository becomes public, and add a row when a PR adds such a file.
Checked on 2026-10-25 (#367) with the full history of all branches (`git fetch --unshallow`).

## Files and data

| File or group | Source | License | May be public |
|---|---|---|---|
| `samples/de-64.3.aoe2record` | [happyleavesaoc/aoc-mgz](https://github.com/happyleavesaoc/aoc-mgz), `tests/recs/de-64.3.aoe2record`, unchanged (#134). The record has the player names of a real game, which are public there too. | MIT, note in `samples/de-64.3.aoe2record.LICENSE.txt` | yes |
| `scx.py` (reader of old `.scx` scenarios) | A port of genie-scx ([SiegeEngineers/genie-rs](https://github.com/SiegeEngineers/genie-rs), `crates/genie-scx`), #311 | GPL-3.0 (the license of aoe2mc too) | yes, while aoe2mc stays GPL-3.0 |
| `tools/mcdata/1.21.1.json`, `tools/mcdata/26.3.json` | Mojang data reports through [misode/mcmeta](https://github.com/misode/mcmeta) (`tools/fetch_mcdata.py`): only the names of blocks, block properties, biomes and entities | Facts about the game, not game assets. The same data is public in misode/mcmeta and in PrismarineJS minecraft-data (MIT). | yes |
| `tools/mcdata/colors-1.21.1.json` | One average color per block side, made from the textures of the Minecraft client jar (`tools/fetch_colors.py`). No texture is in the repository. | Derived numbers, not the textures | yes |
| `docs/images/*-3d.png`, `docs/images/border-*.png` | Renders of `tools/render.py` (own code, own colors file) | GPL-3.0 (this project) | yes |
| `docs/images/examples/*-game.png` | Screenshots of the Minecraft client (`tools/mc_shot.py`) of our own worlds | Mojang allows screenshots of the game in its usage guidelines (not read again here: `minecraft.net` is blocked) | yes |
| `samples/*.aoe2scenario`, `examples/*.aoe2scenario` | Made by this project (`tools/scenarios.py`, #34, #240) from the default scenario of AoE2ScenarioParser | GPL-3.0 (this project); the parser is MIT | yes |
| `tests/golden/tiny.json` | Output of aoe2mc for the tiny test map | GPL-3.0 (this project) | yes |
| `logs/*` (history only, branch `claude/gallant-fermat-csrvkx`, commit `e0d1c10`) | Logs of the offline Minecraft client, removed in `8947f18`. They show the user name "a", container paths and hardware names. No secrets. Not on `main`. | Own output | yes (delete the branch to remove them from the public view) |

Not in the repository and not in its history: reference images of the AoE2 wiki (`tools/refimage.py` writes them to
the scratchpad), Minecraft jars and assets, the owner's old campaigns (#279), game files of AoE2.

## Dependencies

| Package | License | Compatible with GPL-3.0 |
|---|---|---|
| AoE2ScenarioParser 0.9.8 | MIT | yes |
| nbtlib 2.0.4 | MIT | yes |
| numpy | BSD-3-Clause (and 0BSD, MIT, Zlib, CC0-1.0 for parts) | yes |
| pillow | MIT-CMU | yes |
| mgz 1.8.51 | MIT | yes |
| pytest (development) | MIT | yes |
| ruff (development) | MIT | yes |

## Secrets in the history

Scan of `git log -p --all --text` (571 commits, all branches) on 2026-10-25:

- GitHub tokens (`ghp_`, `github_pat_`, `gho_`, `ghs_`), API keys (`sk-`, `sk-ant-`, `AKIA`, `AIza`), Slack tokens
  (`xox`) and private keys (`BEGIN ... PRIVATE KEY`): none.
- Lines with `password`, `secret`, `token`, `api_key` or `credential` and `=` or `:`: only `${{ github.token }}` in the
  workflows, the name `GITHUB_TOKEN` in `framework/tools/dashboard.py`, and the RCON password of `game/run.py`, which
  `secrets.token_hex(16)` makes for each start.

## Personal data in the history

The commit metadata has the name and the personal e-mail address of the owner as the author of the merge commits
(GitHub uses the e-mail address of the account for a squash merge). A public repository shows it. The owner decides:
GitHub setting "Keep my email addresses private" for the next commits, and optionally a history rewrite for the old ones.

## Project license

aoe2mc has the GPL-3.0 (`LICENSE`, `pyproject.toml`). Keep it: `scx.py` is a port of GPL-3.0 code, so a permissive
license (MIT) is possible only without that port. All dependencies are permissive and compatible with GPL-3.0.
