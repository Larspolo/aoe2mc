# The agent system

This document describes the whole system that lets Claude Code agents work on aoe2mc without a person: the parts,
the loop of a run, the locks, the quota pacing, the steering and the setup steps of the owner. Use it to understand
the system, or to set it up for another project. For the rules of the project, read `CLAUDE.md`. For the owner's
controls, read `docs/STEERING.md`. This document links to them and does not copy them.

## The parts

| Part | What it does |
|---|---|
| Two scheduled tasks (owner's account) | "aoe2mc autopilot" starts one run each hour at :06. "aoe2mc pacer heartbeat" wakes the pacer session each hour at :36. |
| Pacer session | One long-lived cloud session. Every 10 minutes it starts the runs that the quota target misses (skill `pacer`). It does no ticket work. |
| Runs | Cloud sessions of the autopilot task. Each run follows the skill `autopilot` with the argument `max`: tickets, one PR each. Many runs work at the same time. |
| Skills (`.claude/skills/`) | The procedures: `autopilot` (the work cycle), `verify` (checks before a push), `ticket` (write and split tickets), `design` (design tickets), `improve` (process review), `roadmap` (epics from `docs/ROADMAP.md`), `pacer`, `operator` (checks and repairs the start of the runs, only in an owner session), `human` (guides the owner through the `needs-human` tickets on the owner's computer), `demo` (a demo game on the owner's computer: a ticket for each feedback in the chat, the cause of each crash, `game/demo_watch.py`), `dashboard-refresh` (the data files of the owner's dashboard artifact, #982). |
| Rules (`CLAUDE.md`, `docs/LEARNINGS.md`) | Each session loads them. `CLAUDE.md` has the commands, the code map and the rules. `docs/LEARNINGS.md` has the lessons for all runs. |
| Tools (`tools/`) | `claim.py` (locks), `usage.py` (quota and the number of runs), `dashboard.py` (the status issue and the pick order), `health.py` (numbers for the review), `tokens.py` (the token sinks of a run), `operator_check.py` (the checks of the `operator` skill), `owner_tasks.py` (the tickets of the `human` skill). |
| GitHub | The issues are the tickets. Issue #1 (label `agent-status`) is the status issue: the dashboard in its body, the run reports as comments. The labels are in `.github/labels.txt`. |
| Workflows (`.github/workflows/`) | CI, Automerge, Unconflict, Claims, Close, Dashboard, Coverage, Labels, Bundles (see below). |
| Cloud environment | The setup script `scripts/cloud-setup.sh` (Java, packages, server jars), the network access, the SessionStart hook. |
| Hooks (`.claude/hooks/`) | `session-start.sh` installs the Python packages, registers the merge driver `merge=jsonl` (#2004) and compares `SETUP_VERSION`. `guard-main.sh` blocks a force push, a history rewrite or a delete of `main`. |

### Workflows

| Workflow | When | What |
|---|---|---|
| `ci.yml` (CI) | Each PR, each push to `main`, each night | Quick checks (lint, fast tests) on each PR; a Markdown-only PR runs only the doc tests (`tools/ci_select.py`, #2089); a change of `game/plugin` also compiles the Paper plugin (#2437). The full suite each night on `main`. A red `main` opens a `P0` ticket. |
| `automerge.yml` (Automerge) | After CI, every 5 minutes, by hand | Merges an agent PR with green CI. Skips `hold` and tickets with `needs-human` or `blocked`. Then starts CI on `main`, Coverage, Claims and Dashboard. |
| `unconflict.yml` (Unconflict) | Every 20 minutes, after each merge | Merges `main` into a conflicted agent PR when git solves the conflict alone (`merge=union` files) or both sides only add lines (`tools/unconflict.py`, #1864; not the same `def` on both sides, and the merge passes `ruff check`, #2631), and starts CI. |
| `claims.yml` (Claims) | A ticket closes, each day | Deletes the claim refs of closed tickets and old comment locks. The runs cannot delete refs (403). |
| `dashboard.yml` (Dashboard) | Every 10 minutes (not on events: the API rate limit, #2168) | Writes the dashboard in the body of the status issue (`tools/dashboard.py`). |
| `coverage.yml` (Coverage) | Each push to `main` | Writes `docs/coverage.md`, `MAX` of `tests/test_coverage.py` and a column of `docs/DESIGN.md`. PRs do not change these files, so they do not conflict there. |
| `metrics.yml` (Metrics) | Each 15 minutes, by hand with `days` | Writes the status issue comments to the orphan branch `metrics` (`tools/metrics_log.py`, one file per day). `tools/health.py` reads them and only the newest comments from the API (#1983). |
| `labels.yml` (Labels) | A change of `.github/labels.txt` | Creates the labels. |

## The loop of a run

1. The pacer session (or the hourly autopilot task) starts a run. The cloud clones the repository on the session
   branch `claude/<name>`.
2. The run reads `CLAUDE.md` and follows the skill `autopilot`. It stops at once when the status issue has `paused`.
   It runs `tools/usage.py --fire`: when the running runs reach the target, it only finishes stalled PRs.
3. It finishes open work first: stalled PRs, red CI, merge conflicts, a red `main`.
4. It reads the new comments of the owner and does what they ask. It sorts new issues (priority, kind, size).
5. It picks a ticket in the order of `tools/dashboard.py --next` (`P0` to `P3`, the least overlap with other work,
   the lowest number) and claims it (`tools/claim.py N`). When the queue is short, it makes new tickets from the
   epics and the roadmap.
6. It does the ticket on its session branch (a later ticket of the run: on `<session branch>-<k>`, `more.md`): a failing test first for a bug, the change, the checks of the skill
   `verify`, and the process improvements (autopilot step 9) in the same PR.
7. It runs `tools/claim.py N --guard`, pushes and opens a PR with `Closes #N`. It does not wait for CI.
8. CI runs the quick checks. Automerge merges the PR when they are green. The merge closes the ticket. Claims
   deletes the claim ref. Dashboard updates the status issue.
9. The run reports on the status issue (a comment with a `Usage:` line and a `Metrics:` line per ticket) and takes
   the next ticket. It stops when no ticket is ready, a usage limit stops it, or its context is above 200k tokens.

## The locks

All locks are git refs. A push without force to a new ref fails when the ref exists, so only one run wins.
The details are in the text at the top of `tools/claim.py`.

| Lock | Ref | Who |
|---|---|---|
| Ticket | `claim/N` (`claim/N-2` ... after a release) | `claim.py N`. The owner beats each 20 minutes (`--beat`). After 30 minutes without a beat the claim is stale: another run can take it over (`--takeover`). `--guard` before each push. |
| Owner comment | `claim/comment-ID` | `claim.py ID --comment`: one run acts on one owner comment. |
| Refill | `claim/refill-E-S` | `claim.py E --refill`: one run makes the sub-issues of epic E (E = 0: the whole queue, one per hour). |
| Process review | `claim/review-<gap>pr-<last>-<k>` | `claim.py 0 --review`: one run runs the `improve` skill after `gap` merged PRs (50). A review with no change doubles the gap (#2039). |
| Roadmap review | `claim/roadmap-100pr-<last>-<k>` | `claim.py 0 --roadmap`: one run reviews `docs/ROADMAP.md` after 100 merged PRs. |

Other rules against conflicts: one ticket per PR, new tests in a new file, new table entries on their own line in
alphabetical order, `merge=union` in `.gitattributes` for files where runs only add lines.

Clock or count (#2039). A rule that waits for work counts merged PRs, because the speed of the project changes and a
fixed time measures a different amount of work: the process review (50 PRs, 100 or 200 after a review with no change),
the roadmap review (100), `Start after: N PRs after #M` and the window of `tools/health.py` (50). A rule that finds a
stopped run or follows a real clock stays in minutes, because a stopped run merges nothing: the claim beat (20), a
stale claim (30, or 10 with the label `conflict`), a "Started by" comment (30), the Automerge sweep (10), an old PR in
`tools/operator_check.py` (30), the pacer (10), `unconflict.yml` (20) and the refill lock (one per hour). The quota
windows (5 hours, 7 days) follow the subscription, the owner comments of `tools/feedback.py` (6 hours) get an answer
in time, and a run longer than 90 minutes is about the context and the container of one run.

## The quota pacing

All runs share the quota of one Claude Max account. `tools/usage.py` reads the 5-hour and the 7-day usage with one
tiny CLI call. It computes the target number of runs: 90 % of the 5-hour window used 2 hours before the reset, then
98 % at the reset, and the week not faster than it passes: when the 7-day usage is ahead of the share of the week
that has passed, the count is at most the runs that the rest of the 7-day budget (1 − used) carries to the 7-day reset
at the measured 7-day burn per run-hour (`health.weekly_burn`, default `BURN7`). This count can be 0: the runs then
wait until the budget per hour is large enough again (#1695). Below `week_free` of `agent.toml` (60 %) of the 7-day
usage there is no weekly guard: the runs fill each 5-hour window (owner, 2026-10-27). The CLI line shows the projection
(`week ahead +38 pt · runs out Wed 11:22`, at the mean rate of the week so far). `--fire` gives the number of runs to start now: the
target less the runs with a claim beat in the last 25 minutes. A run cannot start other runs (no `fire_trigger`, #566),
so the pacer session starts them (at most `max_fire` of `agent.toml` per cycle, and at most the ready tickets plus `refill_runs`: those runs refill the queue). Each cycle reads `.claude/skills/pacer/SKILL.md` again, so a change of the pacing rules reaches
the long-lived pacer session at its next cycle (#1824). `tools/health.py` measures the quota use of one run from the
`Usage:` lines of the run reports, and `usage.py` uses that value. After a plan upgrade the same work is a smaller share of the larger quota: when the burn of
the last 2 hours is less than half of the 24-hour burn, only the last 2 hours count (`health.ratio`, 5-hour and 7-day
burn, #1706). The most runs at one time is `max_runs` in `[pacing]` of `agent.toml` (default 16): raise it when the 5-hour window does not reach its limit (40 since 2026-10-27: at a burn of 0.009 per run-hour, 16 runs used only about 70 %).
The flow brake (owner, 2026-10-27): when CI, merge conflicts or anything else stops the merges, the quota is not the
bottleneck, and more runs only make more open PRs and more conflicts. `--fire` counts the open agent PRs older than
`pr_minutes` without `hold` and the queued CI runs. At `max_waiting_prs` (default 10) it starts at most 1 run per
cycle, at `max_ci_queue` (default 5) none. A run asks `usage.py --flow` in autopilot step 2: with the brake on it only
repairs PRs and takes no new ticket.
A PR with the label `conflict` and no new commit for 10 minutes is stalled: a run takes it over (`claim.py`, #1773).
Automerge adds the label when the merge of a green PR fails, Unconflict when its merge of main finds a real conflict.
The target counts Opus runs. A run of a cheap lane counts its weight (#1727): a Haiku run sets `git config aoe2mc.lane haiku`,
its claims end with ` lane haiku`, the `Usage:` lines count its runs (`· haiku N`), and `health.lane_weights` measures
the weight from them (least squares, at least 10 intervals with Haiku runs; before that `weights` of `agent.toml`,
0.25). `usage.py --fire` gives the ready `lane:haiku` tickets Haiku runs first, then Opus runs take the rest. A lane in `reserved` of `[pacing]` keeps its tickets for its own runs (Opus runs never take them, #1994). `tools/tokens.py` reads the transcript of the
session and writes the `Tokens:` line of each run report: the tokens of the run and its largest sinks. `health.py`
adds them. The `improve` skill finds the largest loss of quota from this data, or the data that is missing, and
makes one `Process: <bottleneck>` ticket for it on the board.

## The steering

The owner steers only through GitHub (`docs/STEERING.md`): new issues with the ticket form, priority labels,
comments, `hold` on a PR, `paused` on the status issue. The agents take instructions only from the owner's login.
An agent asks the owner only on the issue that needs the answer: label `needs-human` and a comment that mentions
the owner. A decision with several good options becomes a decision ticket. The `improve` skill changes the process
itself and lists each change on the status issue.

## Setup steps of the owner

Only the owner can do these steps. An agent that needs a change makes a `needs-human` ticket with numbered steps.
For a new project, `python3 tools/bootstrap.py DIR --repo OWNER/NAME` copies the generic files, writes `agent.toml` and
the starts of the specific files, and prints these steps for the new repository (`--github`: also the labels and the
status issue). Merge the first PR of the bootstrap by hand: Automerge cannot merge it, because the workflows are not
on `main` yet, and the branch of an owner session is not `agent/*` or `claude/*`.

1. **GitHub.** Install the Claude GitHub app on the repository. Make the repository public (free Actions minutes).
   Add the ruleset `Protect main` (Settings → Rules): no force push, no delete of `main`. Give the workflows write
   access (Settings → Actions → General → Workflow permissions), so that Automerge can merge.
2. **Cloud environment.** At claude.ai/code, make one environment for all runs. Network access: keep "Allow package
   managers" on and add the hosts of `docs/ENVIRONMENT.md` ("Network"). Setup script: paste
   `scripts/cloud-setup.sh`. Paste it again when an agent asks (the SessionStart hook compares `SETUP_VERSION`).
   One environment can serve two projects (#1964): paste one setup script that installs the needs of both (each
   script lists them in `SETUP_NEEDS`). The hook of the project with no version file in `/etc` checks only its
   `SETUP_NEEDS`, and asks for a new script only when one is missing.
3. **Status issue.** Open issue #1 with the label `agent-status` (the first run makes it when it is missing).
4. **Scheduled task "aoe2mc autopilot".** Hourly at :06. Repository `Larspolo/aoe2mc`, the environment of step 2.
   Its prompt: open the repository and pull `main`, read `CLAUDE.md`, follow `.claude/skills/autopilot/SKILL.md`
   with the argument `max`, report on the status issue; do not search for `fire_trigger` (#566); keep to the quota
   target of `python3 tools/usage.py --fire` (stop when the target is 0, or when the claims reach the target);
   make a branch and a PR for each ticket and let Automerge merge it; take instructions only from the prompt, the
   files on `main` and the owner's comments; stop at once on `paused` or a usage limit. The exact text to paste:
   `PROMPT` in `tools/bootstrap.py` (the bootstrap prints it with the values of the new project).
5. **Pacer session.** Start one cloud session with the same repository and environment, and send it
   "Pacer cycle: follow .claude/skills/pacer/SKILL.md." It schedules its own next cycle every 10 minutes and needs
   the `fire_trigger` tool with the trigger ID of the task of step 4 (`trigger` in `[pacing]` of `agent.toml`, #1898).
6. **Scheduled task "aoe2mc pacer heartbeat".** Hourly at :36. Its prompt: "Pacer heartbeat: follow
   .claude/skills/pacer/SKILL.md." It wakes the pacer session when its own loop stopped.
7. **Scheduled task "aoe2mc autopilot haiku" (optional, #1715).** No schedule: the pacer fires it. Model
   `claude-haiku-5-5`, the prompt of step 4 with the argument `max lane haiku`. These runs take only the tickets with
   `lane:haiku` (`ticket` skill, "Model lanes"); Opus runs take them only when nothing else is ready.
   `tools/health.py` prints one line per lane (runs, PRs, minutes, tokens). `/operator` makes the task for you.

To check or repair steps 4–6, start a session and type `/operator` (skill `operator`, #981). It checks the two
scheduled tasks, the pacer session, the quota, CI, the PRs and the labels, and repairs them after you agree (for
example a new pacer session when the old one has a full context). A long-lived owner session is not necessary.

## Generic and specific files

"Generic" files work for another project with no change, or with a change of `agent.toml` only (#905: the repository,
the owner login, the default branch, the status issue, the commands, the doc paths). "Specific" files hold rules of aoe2mc.
The tests of the generic tools are generic too, so that a new project has them (#1900). Not in the table: the tests
of `tools/bootstrap.py` (they copy this repository) and the tests that need a specific tool (`tools/dashboard_data.py`,
`tools/release.py`). `tests/test_generic_words.py` fails when a generic file names the domain of the project.
`tests/test_generic_tools.py` fails when a generic file names a `tools/X.py` that is not a generic row (#1963).

| File | Kind | What is specific to aoe2mc |
|---|---|---|
| `agent.toml` | specific | All the project values that the generic files use. `tools/agent_config.py` reads it. |
| `CLAUDE.md` | specific | The commands, the code map, the rules of the domain. The sections "How to work" and "Improve the process" are generic. |
| `docs/STEERING.md` | generic | The owner login. |
| `docs/ENVIRONMENT.md` | specific | The hosts of the tests and the tools of the setup script (Mojang, Java, Minecraft, #1900). |
| `docs/LEARNINGS.md` | specific | The lessons of this project. The first section (environment and GitHub) is mostly generic. |
| `docs/ROADMAP.md` | specific | The three goals and their features. |
| `docs/PRINCIPLES.md` | specific | The direction of the project: the owner's preferences, made general from the decisions. |
| `docs/DECISIONS.md` | specific | The log of the owner's decisions (one line each), the evidence of the principles. |
| `docs/SYSTEM.md` | generic | This document. |
| `.claude/skills/autopilot/SKILL.md` | generic | The issue numbers of the lessons. |
| `.claude/skills/autopilot/conflict.md` | generic | The issue numbers of the lessons (merge conflicts, #1700). |
| `.claude/skills/autopilot/github.md` | generic | The `gh api` paths and the labels. |
| `.claude/skills/autopilot/more.md` | generic | The issue numbers of the lessons (more tickets in one run). |
| `.claude/skills/autopilot/overlap.md` | generic | The issue numbers of the lessons (claims, takeovers). |
| `.claude/skills/autopilot/owner.md` | generic | The issue numbers of the lessons (ask the owner, check tickets). |
| `.claude/skills/autopilot/process.md` | generic | The issue numbers of the lessons (step 9). |
| `.claude/skills/autopilot/queue.md` | generic | The issue numbers of the lessons (epics, refill, haiku lane). |
| `.claude/skills/autopilot/report.md` | generic | The issue numbers of the lessons (step 8, metrics line). |
| `.claude/skills/verify/SKILL.md` | specific | The check levels (preview image, world reader, Minecraft server, screenshots). |
| `.claude/skills/ticket/SKILL.md` | generic | The examples. |
| `.claude/skills/design/SKILL.md` | specific | The design of buildings, units and animals. |
| `.claude/skills/improve/SKILL.md` | generic | The project name. |
| `.claude/skills/roadmap/SKILL.md` | specific | The three goals of aoe2mc. |
| `.claude/skills/operator/SKILL.md` | generic | The task and session names (`aoe2mc autopilot`, `aoe2mc pacer`). |
| `.claude/skills/human/SKILL.md` | specific | The preparation of a play test (worlds, `game/run.py`, Minecraft 26.3). |
| `.claude/skills/demo/SKILL.md` | specific | The demo game (`--random-map arabia`, `game/run.py`, `game/demo_watch.py`, the Minecraft client folders of macOS). |
| `.claude/skills/pacer/SKILL.md` | generic | The trigger ID, the repository path and name (it runs before the clone, so it cannot read `agent.toml`). |
| `.claude/skills/dashboard-refresh/SKILL.md` | specific | The datasets and tabs of the owner's dashboard page (`tools/dashboard_artifact/`, `tools/dashboard_data.py`). |
| `.claude/settings.json` | generic | The permission rules name the repository (they cannot read `agent.toml`). |
| `.claude/hooks/session-start.sh` | generic | The Python packages and the setup version file name. |
| `.claude/hooks/guard-main.sh` | generic | None. |
| `scripts/cloud-setup.sh` | specific | Java, the Minecraft server jars, the Vulkan and X tools of the client. |
| `scripts/autopilot.sh` | generic | None (runs on the owner's computer). |
| `tools/agent_config.py` | generic | None (reads `agent.toml`). |
| `tools/bootstrap.py` | generic | None (sets up this system in a new repository, #906). |
| `tools/claim.py` | generic | None (`agent.toml`). |
| `tools/usage.py` | generic | None. |
| `tools/dashboard.py` | generic | None (`agent.toml`). |
| `tools/feedback.py` | generic | None (`agent.toml`). |
| `tools/health.py` | generic | None (`agent.toml`). |
| `tools/metrics_log.py` | generic | None (the log of the status issue comments on the branch `metrics`, #1983). |
| `tools/report.py` | generic | None (the run report of step 8; the release bar only with a project `tools/release.py`, #1963). |
| `tools/tokens.py` | generic | None. |
| `tools/operator_check.py` | generic | None (`agent.toml`). |
| `tools/owner_tasks.py` | generic | None (`agent.toml`). |
| `tools/unconflict.py` | generic | None (solves add-add conflicts for `unconflict.yml`, #1864). |
| `tools/merge_main.py` | generic | None (merges `main` into a branch in one call: solve, commit, check, push). |
| `tools/cycle_start.py` | generic | None (steps 1 to 5 of the autopilot skill in one call). |
| `tools/ship_pr.py` | generic | None (checks, commit, guard, push and PR of a ticket in one call). |
| `tools/merge_jsonl.py` | generic | None (the merge driver `merge=jsonl`: JSON lines by "name", a line that both sides changed by key and list item, #2004, #2064). |
| `tests/test_agent_config.py` | generic | None (a test of `tools/agent_config.py`). |
| `tests/test_claim.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_active_pr.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_code_span.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_conflict.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_first.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_refill.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_revived.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_takeover.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_dashboard.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_claimed.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_decide.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_muted.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_overlap.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_process.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_start.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_start_prs.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_feedback.py` | generic | None (a test of `tools/feedback.py`). |
| `tests/test_health.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_compare.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_conflicts.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_pr.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_reviews.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_takeovers.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_misses.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_operator.py` | generic | None (a test of `tools/operator_check.py`). |
| `tests/test_owner_tasks.py` | generic | None (a test of `tools/owner_tasks.py`). |
| `tests/test_owner_tasks_close.py` | generic | None (a test of `tools/owner_tasks.py`). |
| `tests/test_owner_tasks_project.py` | generic | None (a test of `tools/owner_tasks.py`). |
| `tests/test_owner_tasks_wait.py` | generic | None (a test of `tools/owner_tasks.py`). |
| `tests/test_report.py` | generic | None (a test of `tools/report.py`). |
| `tests/test_tokens.py` | generic | None (a test of `tools/tokens.py`). |
| `tests/test_tokens_verify.py` | generic | None (a test of `tools/tokens.py`). |
| `tests/test_tokens_cost.py` | generic | None (a test of `tools/tokens.py`). |
| `tests/test_unconflict.py` | generic | None (a test of `tools/unconflict.py`). |
| `tests/test_merge_main.py` | generic | None (a test of `tools/merge_main.py`). |
| `tests/test_cycle_start.py` | generic | None (a test of `tools/cycle_start.py`). |
| `tests/test_ship_pr.py` | generic | None (a test of `tools/ship_pr.py`). |
| `tests/test_merge_jsonl.py` | generic | None (a test of `tools/merge_jsonl.py`). |
| `tests/test_pacer.py` | generic | None (a test of `tools/usage.py`). |
| `tests/test_usage.py` | generic | None (a test of `tools/usage.py`). |
| `tests/test_usage_week.py` | generic | None (a test of `tools/usage.py`). |
| `tests/test_generic_tools.py` | specific | The tools of aoe2mc that generic files may name (`OPTIONAL`, #1963). |
| `tests/test_generic_words.py` | specific | The words of aoe2mc that the generic files must not contain (#1900). |
| `.github/workflows/ci.yml` | specific | The Python, Java and Minecraft steps, the test markers. The red-`main` ticket is generic. |
| `.github/workflows/automerge.yml` | generic | The branch prefixes `claude/*` and `agent/*`. |
| `.github/workflows/unconflict.yml` | generic | None. |
| `.github/workflows/claims.yml` | generic | None. |
| `.github/workflows/close.yml` | generic | None. It closes the issues with the label `close` (#1740). |
| `.github/workflows/dashboard.yml` | generic | None. |
| `.github/workflows/coverage.yml` | specific | The coverage of the AoE2 types. |
| `.github/workflows/metrics.yml` | generic | None. |
| `.github/workflows/labels.yml` | generic | None. |
| `.github/workflows/bundles.yml` | specific | The app bundles of the converter (PyInstaller, `packaging/`, #1541) and their installers (#1542). |
| `.github/workflows/installers.yml` | specific | On a tag `v*`: the installers of `bundles.yml` in the release of the tag (#1542). |
| `.github/workflows/close.yml` | generic | The label `close`: closes the issues that the auto mode does not let a run close (#1740). |
| `.github/workflows/worlds.yml` | specific | The worlds of `examples/` and `samples/` as zips in a release (#207). |
| `.github/labels.txt` | generic | None. |
| `.github/ISSUE_TEMPLATE/ticket.yml` | generic | None. |
| `.gitattributes` | specific | The list of `merge=union` files, and `merge=jsonl` for `game/data/*.jsonl` and `tests/data/civ_bonuses.jsonl` (`tools/merge_jsonl.py`, #2004, #2100). |
