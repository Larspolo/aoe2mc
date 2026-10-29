# Decisions

The log of the owner's decisions: one line per decision, the newest at the end. `docs/PRINCIPLES.md` generalizes
them. Runs only add lines here (`merge=union` in `.gitattributes`).

Columns: date · ticket · decision · recommendation (`taken`, `changed`: the owner combined or changed it, `other`:
the owner chose another option, `-`: no recommendation) · principle (`P<n>`, or `new` when no principle predicts it).

- 2026-10-25 · #23 · Map orientation: `--orientation ne|nw|se|sw`, the suggested default · taken · P3
- 2026-10-25 · #43 · Big cats are hostile wolves, not ocelots · - · P1
- 2026-10-25 · #219 · Custom biomes: option C, default B; switch the default when the warning goes away · changed · P3, P4
- 2026-10-25 · #246 · World border default: diorama · - · new
- 2026-10-25 · #357 · Order of the gameplay milestones: A C D B E F · - · new
- 2026-10-26 · #431 · Minecraft path finding through a Paper plugin; Minecraft features first · - · P2
- 2026-10-26 · #587 · Use 90 % of each 5-hour window 2 hours before the reset, then 98 % · - · P7
- 2026-10-26 · #618 · Building choices in a Paper chest menu · - · P8
- 2026-10-26 · #623 · Ask the owner only when several clear options have no single best one, on GitHub · - · P5
- 2026-10-26 · #658 · Hit points: the name line with hearts (A) and shown only when hurt or selected (C) · changed · P9
- 2026-10-26 · #668 · Assign a check only when the agent thinks it is fully okay · - · P5
- 2026-10-26 · #686 · Replay controls: hotbar items, a chest for more, each action also a command · other · P8
- 2026-10-26 · #745 · Selection box with two corners; control groups later · taken · P4
- 2026-10-26 · #782 · Watcher mode: adventure mode with flight and a right-click toolbar · changed · P3
- 2026-10-26 · #797 · Action hints in the action bar · taken · P9
- 2026-10-26 · #820 · An epic checks its whole scope · - · P6
- 2026-10-26 · #862 · Ask the owner only on the issue · - · P5
- 2026-10-26 · #878 · 100 % = the full roadmap (C); A and B only as indications · - · P6
- 2026-10-26 · #961 · Random maps: A and B · changed · P4
- 2026-10-26 · #992 · Selection: hold right click (Paper); vanilla keeps two clicks · taken · P1, P3
- 2026-10-26 · #1096 · Horses: scale 0.7 everywhere · taken · P2
- 2026-10-26 · #1106 · Stances: a chest menu, as the villager · taken · P8
- 2026-10-26 · #1159 · Never ask the owner for times or values; test them · - · P5
- 2026-10-27 · #1232 · Flare: a menu entry and `/trigger`, no new hotbar item · other · P8
- 2026-10-27 · #1301 · Replay terrain fog: the minimap only (C) · other · new
- 2026-10-27 · #1308 · Player side: A for now, expand with C · other · P4
- 2026-10-27 · #1314 · Tribute: one hotbar item for the top-right AoE2 buttons · taken · P8
- 2026-10-27 · #1323 · A gate opens for own units · taken · P1
- 2026-10-27 · #1525 · Siege: mobs in minecarts, no overlap · changed · P1
- 2026-10-27 · #1544 · Installers stay unsigned · taken · P3
- 2026-10-27 · #1625 · Fog only with `--ambience full` or `--fog` · changed · P3
- 2026-10-27 · #1629 · Find the bottleneck from data; tokens are a hunch · - · P7
- 2026-10-27 · #1674 · Check if the owner is really needed; group the owner's tickets in one game · - · P5
- 2026-10-27 · #1708 · A check closes on the agent's evidence; the owner checks a sample (`owner-sample`) · taken · P5
- 2026-10-27 · #1786 · Selection box: hold right click with the command stick on Paper, no wand · - · P8
- 2026-10-27 · #1828 · Go to places with a compass menu; the F key stays free · changed · P1, P4
- 2026-10-27 · #1702 · Generalise: put the large tables into line-based data files, not only `train.TRAINS` · other · new (P10)
- 2026-10-27 · #1909 · All game data in data files, by content, not by size; a lint, not a question for each run; measure in merged PRs, not hours · changed · P10
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
- 2026-10-29 · - · No test checks the content of a data file or a configuration file; remove such tests · - · P10
- 2026-10-29 · - · The improve loop learns from the owner's own system changes (owner work makes the next review come soon), checks all levers in each review, makes bold changes (also redesigns, also with a pause for owner steps), and waits by merged PRs, never by hours · - · new (P11)
- 2026-10-29 · - · The gap between process reviews follows their results: while reviews make changes it halves from 80 merged PRs down to 10, while they make none it doubles from 80 up to 640, and each turn of the result resets it to 80 · - · P11
