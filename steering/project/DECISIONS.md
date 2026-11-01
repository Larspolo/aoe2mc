# Decisions: the project

The log of the owner's decisions: one line per decision, the newest at the end. `steering/project/PRINCIPLES.md` generalizes
them. Runs only add lines here (`merge=union` in `.gitattributes`).

Columns: date · ticket · decision · recommendation (`taken`, `changed`: the owner combined or changed it, `other`:
the owner chose another option, `-`: no recommendation) · principle (`P<n>`, or `new` when no principle predicts it).

- 2026-10-25 · #23 · Map orientation: `--orientation ne|nw|se|sw`, the suggested default · taken · P3
- 2026-10-25 · #43 · Big cats are hostile wolves, not ocelots · - · P1
- 2026-10-25 · #219 · Custom biomes: option C, default B; switch the default when the warning goes away · changed · P3, P4
- 2026-10-25 · #246 · World border default: diorama · - · new
- 2026-10-25 · #357 · Order of the gameplay milestones: A C D B E F · - · new
- 2026-10-26 · #431 · Minecraft path finding through a Paper plugin; Minecraft features first · - · P2
- 2026-10-26 · #618 · Building choices in a Paper chest menu · - · P8
- 2026-10-26 · #658 · Hit points: the name line with hearts (A) and shown only when hurt or selected (C) · changed · P9
- 2026-10-26 · #686 · Replay controls: hotbar items, a chest for more, each action also a command · other · P8
- 2026-10-26 · #745 · Selection box with two corners; control groups later · taken · P4
- 2026-10-26 · #782 · Watcher mode: adventure mode with flight and a right-click toolbar · changed · P3
- 2026-10-26 · #797 · Action hints in the action bar · taken · P9
- 2026-10-26 · #961 · Random maps: A and B · changed · P4
- 2026-10-26 · #992 · Selection: hold right click (Paper); vanilla keeps two clicks · taken · P1, P3
- 2026-10-26 · #1096 · Horses: scale 0.7 everywhere · taken · P2
- 2026-10-26 · #1106 · Stances: a chest menu, as the villager · taken · P8
- 2026-10-27 · #1232 · Flare: a menu entry and `/trigger`, no new hotbar item · other · P8
- 2026-10-27 · #1301 · Replay terrain fog: the minimap only (C) · other · new
- 2026-10-27 · #1308 · Player side: A for now, expand with C · other · P4
- 2026-10-27 · #1314 · Tribute: one hotbar item for the top-right AoE2 buttons · taken · P8
- 2026-10-27 · #1323 · A gate opens for own units · taken · P1
- 2026-10-27 · #1525 · Siege: mobs in minecarts, no overlap · changed · P1
- 2026-10-27 · #1544 · Installers stay unsigned · taken · P3
- 2026-10-27 · #1625 · Fog only with `--ambience full` or `--fog` · changed · P3
- 2026-10-27 · #1786 · Selection box: hold right click with the command stick on Paper, no wand · - · P8
- 2026-10-27 · #1828 · Go to places with a compass menu; the F key stays free · changed · P1, P4
- 2026-10-27 · #2055 · Transport ship: the ship sails to the shore of the units first, then they board (changes #1653) · changed · P1
- 2026-10-28 · #2648 · Bot difficulty: the six AoE2 names, the values of each level in a data file · taken · P1
- 2026-10-28 · #2585 · Minimap click: a map in an item frame near the town center, a wand click on a pixel · taken · P2, P1
- 2026-10-28 · #2233 · Taunts: a vanilla sound only with a good Minecraft match, else text only · other · P3, P1
- 2026-10-28 · #2808 · Production panel of the live replay: a text display with a progress bar above each producing building (C), no boss bar per player · other · P9, P1
- 2026-10-28 · #3103 · Player 1 defeated in a game of more than two: as AoE2, the others play on, and a team wins together (A) · taken · P1, P10
- 2026-10-28 · #3275 · Resources left: a text display above each partially drained resource (B) · taken · P9
- 2026-10-29 · #3447 · Live graphs of the replay: a text display "chart" in the sky, one row of bar characters per player (B); the owner checks the graphs in the game, a map item (A) can come later · taken · P2, P3, P4
- 2026-10-29 · #3583 · Antiquity Mode (Return of Rome): epic #2263 excludes it now; a later roadmap feature `play:antiquity` adds the Return of Rome civilizations, ages, units and technologies (B) · taken · P4, P6, P1
- 2026-10-29 · #3760 · Art of War challenges: own challenge maps of `tools/scenarios.py` with the start units, civilization, bot, goal and medal limits from `game/data/challenges.jsonl` (A), not the original DE scenario files · taken · P5, P4
- 2026-10-30 · #4754 · Hidden civilizations: the lobby and diplomacy menus show "Player 2 (?)" for an enemy player (A), as AoE2 DE · taken · P1
- 2026-10-31 · #5052 · Random map labels: `FIXED_POSITIONS` is true when the lobby box "Team Together" is on (the DE scripting guide, A); `TEAM_GAME` and `TEAMS_CONNECTED` are not in the guide: switches of the script authors, never defined (B) · taken · P1
- 2026-10-31 · #5120 · XS scripts of scenarios: epic #5119 waits until after the release (`after-release`); then both A (an XS interpreter in the game program) and B (XS compiled to datapack functions, for vanilla worlds) · changed · P1, P2, P3, P4
- 2026-10-31 · #5378 · The texts in other languages: after the release, C: the unit, building and technology names from the AoE2 DE string tables of the local install (A: a tool writes the lang files on that computer only; no AoE2 texts in the repository or in a GPL bundle; a shared copy needs the notice and the link of the Microsoft Game Content Usage Rules), the own sentences by agent translations (B) · taken · P1
- 2026-11-01 · - · Release focus: until the next release only bugs, release checks, the features of milestones B and A and the user experience of the play test; all other features (milestone C, mods, languages, achievements, analysis, extra replay modes, export) wait with `after-release` · - · new
- 2026-11-01 · - · Release cycle: a release epic "Release vX.Y.Z" holds the scope; its close tags the release (GitHub release, installers, worlds) when CI is green; then all held tickets come back, ranked against each other (P1 to P3, `muted` for a ticket that must not come back now), and the next release epic starts; a new feature goes in or out by comparison with the held tickets · taken · new
