# Decisions: the agent system

The log of the owner's decisions: one line per decision, the newest at the end. `steering/system/PRINCIPLES.md` generalizes
them. Runs only add lines here (`merge=union` in `.gitattributes`).

Columns: date · ticket · decision · recommendation (`taken`, `changed`: the owner combined or changed it, `other`:
the owner chose another option, `-`: no recommendation) · principle (`P<n>`, or `new` when no principle predicts it).

- 2026-10-26 · #587 · Use 90 % of each 5-hour window 2 hours before the reset, then 98 % · - · P7
- 2026-10-26 · #623 · Ask the owner only when several clear options have no single best one, on GitHub · - · P5
- 2026-10-26 · #668 · Assign a check only when the agent thinks it is fully okay · - · P5
- 2026-10-26 · #820 · An epic checks its whole scope · - · P6
- 2026-10-26 · #862 · Ask the owner only on the issue · - · P5
- 2026-10-26 · #878 · 100 % = the full roadmap (C); A and B only as indications · - · P6
- 2026-10-26 · #1159 · Never ask the owner for times or values; test them · - · P5
- 2026-10-27 · #1629 · Find the bottleneck from data; tokens are a hunch · - · P7
- 2026-10-27 · #1674 · Check if the owner is really needed; group the owner's tickets in one game · - · P5
- 2026-10-27 · #1708 · A check closes on the agent's evidence; the owner checks a sample (`owner-sample`) · taken · P5
- 2026-10-27 · #1702 · Generalise: put the large tables into line-based data files, not only `train.TRAINS` · other · new (P10)
- 2026-10-27 · #1909 · All game data in data files, by content, not by size; a lint, not a question for each run; measure in merged PRs, not hours · changed · P10
- 2026-10-29 · - · No test checks the content of a data file or a configuration file; remove such tests · - · P10
- 2026-10-29 · #4242 · A change of data files only adds no test, also a menu or bonus test of the new line; a check of `tools/ship_pr.py` stops it · - · P10
- 2026-10-29 · - · The improve loop learns from the owner's own system changes (owner work makes the next review come soon), checks all levers in each review, makes bold changes (also redesigns, also with a pause for owner steps), and waits by merged PRs, never by hours · - · new (P11)
- 2026-10-29 · - · The gap between process reviews follows their results: while reviews make changes it halves from 80 merged PRs down to 10, while they make none it doubles from 80 up to 640, and each turn of the result resets it to 80 · - · P11
- 2026-10-29 · #4197 · The agent framework stays in aoe2mc, and `tools/bootstrap.py` copies it into a new project (A); a synced repository (B) waits until there are more projects · other · P4
