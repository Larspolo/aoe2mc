# The agent system

This document describes the whole system that lets Claude Code agents work on aoe2mc without a person: the parts,
the loop of a run, the locks, the quota pacing, the steering and the setup steps of the owner. Use it to understand
the system, or to set it up for another project. For the rules of the project, read `CLAUDE.md`. For the owner's
controls, read `docs/STEERING.md`. This document links to them and does not copy them.

## The parts

| Part | What it does |
|---|---|
| Scheduled tasks (owner's account) | "aoe2mc autopilot", "aoe2mc autopilot haiku" and "aoe2mc autopilot deep" have no schedule: the pacer starts them (since 2026-10-28 the workflow `pacer.yml` through their API triggers, #3194). |
| Pacer | The workflow `pacer.yml` (`tools/pacer.py`, #3193): every 10 minutes it starts the runs that the quota target misses, through the API triggers of the scheduled tasks. |
| Runs | Cloud sessions of the autopilot task. Each run follows the skill `autopilot` with the argument `max`: tickets, one PR each. Many runs work at the same time. |
| Skills (`.claude/skills/`) | The procedures: `autopilot` (the work cycle), `verify` (checks before a push), `ticket` (write and split tickets), `design` (design tickets), `improve` (process review), `roadmap` (epics from `docs/ROADMAP.md`), `human` (guides the owner through the `needs-human` tickets on the owner's computer), `demo` (a demo game on the owner's computer: a ticket for each feedback in the chat, the cause of each crash, `game/demo_watch.py`). |
| Denied tools (`.claude/settings.json`) | The `deny` list removes the session tools that no skill uses (`Artifact`, `Workflow`, the `Suggest*` and `Search*` tools, and since 2026-10-29 the plan, worktree, task list, wake-up, notification and review-findings tools and the
session task tools `mcp__ccd_session` ...) from each session of the repository: their descriptions were about 19,000 of the 66,000 base tokens of each call (2026-10-28). A rule in a file that the SessionStart hook writes works only from the next session, so the list is in the repository. |
| Rules (`CLAUDE.md`, `docs/LEARNINGS.md`) | Each session loads them. `CLAUDE.md` has the commands, the code map and the rules. `docs/LEARNINGS.md` has the lessons for all runs. |
| Tools (`tools/`) | `claim.py` (locks), `usage.py` (quota and the number of runs), `dashboard.py` (the status issue and the pick order), `health.py` (numbers for the review), `tokens.py` (the token sinks of a run), `operator_check.py` (the checks of the `operator` skill), `owner_tasks.py` (the tickets of the `human` skill). |
| GitHub | The issues are the tickets. Issue #1 (label `agent-status`) is the status issue: the dashboard and the state comment in its body. The run reports are files on the branch `metrics` (`runs/`, 2026-10-29; before: comments on the status issue). The labels are in `.github/labels.txt`. |
| Workflows (`.github/workflows/`) | CI, Automerge, Unconflict, Claims, Close, Dashboard, Coverage, Labels, Bundles (see below). |
| Cloud environment | The setup script `scripts/cloud-setup.sh` (Java, packages, server jars), the network access, the SessionStart hook. |
| Hooks (`.claude/hooks/`) | `session-start.sh` installs the Python packages (a pip pillow and setuptools if the Debian ones are there), registers the merge driver `merge=jsonl` (#2004), sets an empty `TMPDIR` to `/tmp` and compares `SETUP_VERSION`. `guard-main.sh` blocks a force push, a history rewrite or a delete of `main`. `guard-shell.sh` blocks the shell pitfalls of `docs/LEARNINGS.md`: `cat > FILE <<` over a tracked file, a redirect into `$VAR/` with an empty variable, a variable set in a list that `&` puts in the background, an unquoted heredoc tag with `` ` `` in the body, `pkill -f` with no bracket in the pattern, and `git stash` or `git checkout --ours` in a merge. |

### Workflows

| Workflow | When | What |
|---|---|---|
| `ci.yml` (CI) | Each PR, each push to `main`, each night | Quick checks (lint, fast tests) on each PR; a Markdown-only PR runs only the doc tests (`tools/ci_select.py`, #2089); a change of `game/plugin` also compiles the Paper plugin (#2437). The full suite each night on `main`. A red `main` opens a `P0` ticket; a green `main` after a red one starts Unconflict (#3685). |
| `automerge.yml` (Automerge) | After CI, every 5 minutes, by hand | Merges an agent PR with green CI, and a PR on any branch with the label `automerge` (#3383). Skips `hold` (it wins over `automerge`) and tickets with `needs-human` or `blocked`. When GitHub calls the PR `dirty`, it merges `main` into it with our merge drivers and `tools/unconflict.py` (`land()`), checks `ruff`, pushes and merges at once, with no new CI run (#3199); only a real conflict gets `conflict`, not a merge that failed because another merge landed in the same second (#3063). Then starts CI on `main`, Coverage and Claims (not Dashboard: the pacer starts it each cycle, 2026-10-29). |
| `unconflict.yml` (Unconflict) | Every 20 minutes, after each merge | Merges `main` into a conflicted agent PR when git solves the conflict alone (`merge=union` files) or both sides only add lines (`tools/unconflict.py`, #1864; not the same `def` on both sides, and the merge passes `ruff check`, #2631), and starts CI. When `main` is green again, it also merges `main` into a PR whose last CI run failed while `main` was red, and starts CI (#3685): no run must take it over. `tools/unconflict_pick.py` finds the PRs with git (`merge-tree` with no merge attributes, as GitHub merges) and 3 to 4 API calls, not 3 + 2 calls per open PR (2026-10-29). |
| `claims.yml` (Claims) | A ticket closes, after each merge, each day | Deletes the claim refs of closed tickets and old locks (`claim.py 0 --prune`: git and one API read; the REST script used about 60 calls a run, 2026-10-29). The runs cannot delete refs (403). |
| `dashboard.yml` (Dashboard) | Each pacer cycle (10 minutes), the cron as a fallback (not on events and not after each merge: the API rate limit, #2168, 2026-10-29) | Writes the dashboard in the body of the status issue (`tools/dashboard.py`). |
| `pacer.yml` (Pacer) | One run loops for 5.5 hours (a cycle every 10 minutes), then starts the next run; the cron (`*/30`) only restarts a dead loop: GitHub fires the cron schedules of this repository a few times per day | Only while `pacer = "workflow"` in `[pacing]` of `agent.toml`: starts the runs that the quota target misses through the API trigger of each task (`tools/pacer.py`, #3193). Each cycle also starts `dashboard-site.yml` and `dashboard.yml`, and writes the new status comments and its own record (quota, burns, target, claims, ready tickets, planned and started runs, the REST budget of the workflow token: `pacer.py --log`) to the branch `metrics` (`status/` and `pacer/`, `metrics_log.py --push`, 2026-10-29). Secrets: `CLAUDE_CODE_OAUTH_TOKEN` (the quota read), `PACER_URL_<TASK>` and `PACER_TOKEN_<TASK>` for `MAIN`, `HAIKU`, `DEEP`. A task takes at most 30 API starts per hour, an account 100. |
| `dashboard-site.yml` (Dashboard site) | Each pacer cycle (`pacer.yml` starts it), the cron as a fallback, by hand | Builds the owner's dashboard (`tools/dashboard_site.py`: the page of `tools/dashboard_artifact/`, the data of `tools/dashboard_data.py`) and publishes it to GitHub Pages (owner decision A, 2026-10-28). It replaces the hourly Claude task "aoe2mc dashboard refresh" and the artifact (the skill `dashboard-refresh` was removed with the `Artifact` tool, 2026-10-28). `actions/cache` keeps the issues and PRs of the last build: a build reads only the changed ones (`dashboard_data.cached`), all of them once a day (2026-10-29: about 60 API pages a build before). |
| `coverage.yml` (Coverage) | Each push to `main` | Writes `docs/coverage.md`, `MAX` of `tests/test_coverage.py` and a column of `docs/DESIGN.md`. PRs do not change these files, so they do not conflict there. |
| `metrics.yml` (Metrics) | The cron (`*/15`, a few times a day), by hand with `days` | Writes the status issue comments to the orphan branch `metrics` (`tools/metrics_log.py`, one file per day). `tools/health.py` reads them, the run reports of `runs/` (each run adds its own file, `metrics_log.post`) and only the newest comments from the API (#1983). The tip keeps the last 14 days (`metrics_log.prune`: each reader fetches the whole tip); the git history of the branch keeps all days. A store outside GitHub (Cloudflare D1, free up to 5 million rows read a day) was not better: it adds an account, a token in the runs and a way to fail for the pacer (2026-10-29). The pacer loop writes the branch in each cycle too (2026-10-29): this workflow is the fallback and the backfill. |
| `labels.yml` (Labels) | A change of `.github/labels.txt` | Creates the labels. |

### Tools of the system

| Task | Command |
|---|---|
| System numbers | `python3 tools/health.py [--hours N]` (CI, setup, takeovers, conflicts, files in git; `improve` skill) |
| Start of the runs | `python3 tools/operator_check.py` (quota, ready tickets, CI, old PRs, labels, owner comments; the scheduled tasks and the pacer: `docs/OPERATOR.md`, #981) |
| Owner feedback | `python3 tools/feedback.py` (the owner comments of the last 6 hours without a lock `claim/comment-ID`, autopilot step 3, #971) |
| Tokens of a run | `python3 tools/tokens.py [--top N]` (the tokens of this session and the largest sinks: files, commands; the `Tokens:` line of the run report; `--verify`: the minutes of each check command) |
| Quota and pacing | `python3 tools/usage.py` (5-hour and 7-day usage, resets; `--target`: the number of runs (90 % of the 5-hour window 2 hours before the reset, then 98 %); `--sample`: the `Usage:` line of the run report; `--fire`: the runs that the pacer starts now; `tools/pacer.py` starts them, `pacer.yml`, #3193) |
| Dashboard of #1 | `python3 tools/dashboard.py --dry-run` (`--next`: ticket candidates in pick order) |
| Release bar | `python3 tools/release.py` (percent of each goal for the milestones C = 100 %, A and B: `docs/RELEASE.md`, #878) |

## The loop of a run

1. The pacer (`pacer.yml`) starts a run. The cloud clones the repository on the session
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
9. The run adds its report to the branch `metrics` (`report.py --post`: a `Usage:` line and a `Metrics:` line per ticket) and takes
   the next ticket. It stops when no ticket is ready, a usage limit stops it, or its context is 120k tokens or more.

## The locks

All locks are git refs. A push without force to a new ref fails when the ref exists, so only one run wins.
The details are in the text at the top of `tools/claim.py`.

| Lock | Ref | Who |
|---|---|---|
| Ticket | `claim/N` (`claim/N-2` ... after a release) | `claim.py N`. The owner beats each 20 minutes (`--beat`). After 30 minutes without a beat the claim is stale: another run can take it over (`--takeover`). `--guard` before each push. |
| Owner comment | `claim/comment-ID` | `claim.py ID --comment`: one run acts on one owner comment. |
| Refill | `claim/refill-E-S` | `claim.py E --refill`: one run makes the sub-issues of epic E (E = 0: the whole queue, one per hour). |
| Process review | `claim/review-<gap>pr-<last>-<k>` | `claim.py 0 --review`: one run runs the `improve` skill after `gap` merged PRs (`[review]` of `agent.toml`, no hours: owner, 2026-10-29). A review with no change doubles the gap (#2039). Owner work since the last review (a merge with no commit of a run: each run commit has the trailer `Agent-Run:` of the `commit-msg` hook of `cycle_start.py`) makes the gap `owner_gap`. |
| Roadmap review | `claim/roadmap-100pr-<last>-<k>` | `claim.py 0 --roadmap`: one run reviews `docs/ROADMAP.md` after 100 merged PRs. |

Other rules against conflicts: one ticket per PR, new tests in a new file, new table entries on their own line in
alphabetical order, `merge=union` in `.gitattributes` for files where runs only add lines.

Clock or count (#2039). A rule that waits for work counts merged PRs, because the speed of the project changes and a
fixed time measures a different amount of work: the process review (`gap`, `max_gap` and `owner_gap` of `[review]` in `agent.toml`),
the roadmap review (100), `Start after: N PRs after #M` and the window of `tools/health.py` (50). A rule that finds a
stopped run or follows a real clock stays in minutes, because a stopped run merges nothing: the claim beat (20), a
stale claim (30, or 10 with the label `conflict`), a "Started by" comment (30), the Automerge sweep (10), an old PR in
`tools/operator_check.py` (30), the pacer (10), `unconflict.yml` (20) and the refill lock (one per hour). The quota
windows (5 hours, 7 days) follow the subscription, the owner comments of `tools/feedback.py` (6 hours before the
last run report, at most 23, #3060) get an answer in time, and a run longer than 90 minutes is about the context and
the container of one run. A wait to measure a change never names a date (owner, 2026-10-29): `tools/health.py` lists the
open tickets with a date in their `Start after:` line ("Time waits", lever 8 of the `improve` skill).

## The quota pacing

All runs share the quota of one Claude Max account. `tools/usage.py` reads the 5-hour and the 7-day usage with one
tiny CLI call. It computes the target number of runs: 90 % of the 5-hour window used 2 hours before the reset, then
98 % at the reset, and the week not faster than it passes: when the 7-day usage is ahead of the share of the week
that has passed, the count is at most the runs that the rest of the 7-day budget (1 − used) carries to the 7-day reset
at the measured 7-day burn per run-hour (`health.weekly_burn`, default `BURN7`). This count can be 0: the runs then
wait until the budget per hour is large enough again (#1695). Below `week_free` of `agent.toml` (60 %) of the 7-day
usage there is no weekly guard: the runs fill each 5-hour window (owner, 2026-10-27). `week_guard` of `agent.toml` turns the weekly guard on
(`true`) or off (`false`: only the 5-hour window counts; owner, 2026-10-28). The CLI line shows the projection
(`week ahead +38 pt · runs out Wed 11:22`, at the mean rate of the week so far). `--fire` gives the number of runs to start now: the
target less the runs with a claim beat in the last 25 minutes, and less the runs that the pacer started in the last 12 minutes and
that have no claim yet (`usage.pending`, from the `--log` of `pacer.py`; each takes a ready ticket of its lane, 2026-10-29). A run cannot start other runs (no `fire_trigger`, #566),
so the pacer starts them (at most `max_fire` of `agent.toml` per cycle, and at most the ready tickets plus `refill_runs`: those runs refill the queue). The pacer is the workflow `pacer.yml` (#3193, #3194): each cycle fetches `main` and runs
`tools/pacer.py`, so a change of the pacing rules works at the next cycle. It starts each run with one call of the
API trigger of its task; a task takes at most 30 API starts per hour (an account 100), and when a lane task answers
HTTP 429 its runs go to the main task. `tools/health.py` measures the quota use of one run from the
`Usage:` lines of the run reports, and `usage.py` uses that value. After a plan upgrade the same work is a smaller share of the larger quota: when the burn of
the last 2 hours is less than half of the 24-hour burn, only the last 2 hours count (`health.ratio`, 5-hour and 7-day
burn, #1706). The most runs at one time is `max_runs` in `[pacing]` of `agent.toml` (default 16): raise it when the 5-hour window does not reach its limit (40 since 2026-10-27: at a burn of 0.009 per run-hour, 16 runs used only about 70 %).
The flow brake (owner, 2026-10-27): when CI, merge conflicts or anything else stops the merges, the quota is not the
bottleneck, and more runs only make more open PRs and more conflicts. `--fire` counts the open agent PRs older than
`pr_minutes` without `hold` and the queued CI runs. At `max_waiting_prs` (default 10) it starts at most 1 run per
cycle, at `max_ci_queue` (default 5) none. A run asks `usage.py --flow` in autopilot step 2: with the brake on it only
repairs PRs and takes no new ticket.
A PR with the label `conflict` and no new commit for 10 minutes is stalled: a run takes it over (`claim.py`, #1773).
Automerge adds the label when its own merge of main with the drivers finds a real conflict (#3199), Unconflict when its merge of main finds a real conflict.
The target counts Opus runs. A run of a cheap lane counts its weight (#1727): a Haiku run sets `git config aoe2mc.lane haiku`,
its claims end with ` lane haiku`, the `Usage:` lines count its runs (`· haiku N`), and `health.lane_weights` measures
the weight from them (least squares, at least 10 intervals with Haiku runs; before that `weights` of `agent.toml`,
0.25). `usage.py --fire` gives the ready `lane:haiku` tickets Haiku runs first, then Opus runs take the rest. A lane in `reserved` of `[pacing]` keeps its tickets for its own runs (Opus runs never take them, #1994). `tools/tokens.py` reads the transcript of the
session and writes the `Tokens:` line of each run report: the tokens of the run and its largest sinks. `health.py`
adds them. The `Run:` line (`tokens.py --run-line`, 2026-10-29) names the session, the branch, the start, the wall minutes, the
model, the effort, the thinking tokens, the eq of each phase and of each ticket, and the lane: it joins the reports of
one run and the starts of the pacer, so that a run that stops with no report shows. The `improve` skill finds the largest loss of quota from this data, or the data that is missing, and
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
on `main` yet.

1. **GitHub.** Install the Claude GitHub app on the repository. Make the repository public (free Actions minutes).
   Add the ruleset `Protect main` (Settings → Rules): no force push, no delete of `main`. Give the workflows write
   access (Settings → Actions → General → Workflow permissions), so that Automerge can merge. To let Automerge merge
   a PR of your own branch, add the label `automerge` to it (#3383).
2. **Cloud environment.** At claude.ai/code, make one environment for all runs. Network access: keep "Allow package
   managers" on and paste the whole file `scripts/allowed-domains.txt` into "Allowed domains". Paste it again when an
   agent asks (it adds a host to the file and opens a `needs-human` ticket, `docs/ENVIRONMENT.md`, "Network"). Setup script: paste
   `scripts/cloud-setup.sh`. Paste it again when an agent asks (the SessionStart hook compares `SETUP_VERSION`).
   One environment can serve two projects (#1964): paste one setup script that installs the needs of both (each
   script lists them in `SETUP_NEEDS`). The hook of the project with no version file in `/etc` checks only its
   `SETUP_NEEDS`, and asks for a new script only when one is missing.
3. **Status issue.** Open issue #1 with the label `agent-status` (the first run makes it when it is missing).
4. **Scheduled task "aoe2mc autopilot".** No schedule: the pacer starts it (2026-10-28; before: hourly at :06). Repository `Larspolo/aoe2mc`, the environment of step 2.
   Its prompt is only `/scheduled max` (owner, 2026-10-29): the skill `.claude/skills/scheduled/SKILL.md` holds the
   rules (`CLAUDE.md` is already in the context, follow the `autopilot` skill, no `fire_trigger` (#566), the quota target of
   `python3 tools/usage.py --fire`, a branch and a PR for each ticket, instructions only from the owner, stop on
   `paused` or a usage limit), so a PR changes them and no task needs an edit.
5. **Pacer (`pacer.yml`, #3193, #3194).** On your computer run `claude setup-token`, and add the token as the
   repository secret `CLAUDE_CODE_OAUTH_TOKEN` (the quota read). For each autopilot task (steps 4, 7, 8): in the
   app, edit the task, add an API trigger, generate a token, and add the secrets `PACER_URL_<TASK>` (the fire URL)
   and `PACER_TOKEN_<TASK>` (the token) with `<TASK>` = `MAIN`, `HAIKU`, `DEEP`. Keep `pacer = "workflow"` in
   `[pacing]` of `agent.toml`. Then start Actions → Pacer → Run workflow once: the run loops and starts the next
   run itself. A new token makes the old one invalid: change the secret too.
6. (Removed in #3427: the pacer session, skill `pacer`.)
7. **Scheduled task "aoe2mc autopilot haiku" (optional, #1715).** No schedule: the pacer fires it. Model
   `claude-haiku-5-5`, the prompt `/scheduled max lane haiku`. These runs take only the tickets with
   `lane:haiku` (`ticket` skill, "Model lanes"); Opus runs take them only when nothing else is ready.
   `tools/health.py` prints one line per lane (runs, PRs, minutes, tokens). `docs/OPERATOR.md`, section 3, makes the task.
8. **Scheduled task "aoe2mc autopilot deep" (owner, 2026-10-28).** No schedule: the pacer fires it. Model
   `claude-opus-5-5` at effort high (the owner's setting; the main task runs at low effort), the prompt
   `/scheduled max lane deep`. These runs take the tickets with `lane:deep` and do the epic check, the queue refill, the roadmap
   review and the process review (`autopilot/queue.md`, "Deep lane").
9. **Move to another Claude account (owner, 2026-10-28).** Follow `docs/OPERATOR.md`, section 4 (or start a session
   in the new account with the repository and let it follow the section). The steps pause the runs (label `paused`),
   make the tasks of steps 4, 7 and 8, write the new IDs to `agent.toml`, and check all parts at the end. The steps
   that only you can do:
   - In the old account: disable the scheduled tasks of aoe2mc (their API tokens stop with them).
   - The secrets of step 5: a new `claude setup-token` of the new account and new API triggers of the new tasks.
   - In the new account: connect GitHub (the Claude GitHub app stays on the repository); make the cloud environment
     of step 2; set the repository, the model and the effort of each new task (autopilot: Opus 5.5, effort low;
     haiku: Haiku 5.5; deep: Opus 5.5, effort high). The tool cannot set these three values.
   The GitHub side (tickets, claims, labels, the status issue) does not change.

To check or repair steps 4–8, follow `docs/OPERATOR.md` (#981). It checks the scheduled
tasks, the runs of `pacer.yml`, the quota, CI, the PRs and the labels, and repairs them after you agree. A long-lived owner session is not necessary.

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
| `.claude/skills/scheduled/SKILL.md` | generic | The rules of a scheduled run: the prompt of each task is `/scheduled ARGUMENT`. |
| `.claude/skills/verify/SKILL.md` | specific | The check levels (preview image, world reader, Minecraft server, screenshots). |
| `.claude/skills/ticket/SKILL.md` | generic | The examples. |
| `.claude/skills/design/SKILL.md` | specific | The design of buildings, units and animals. |
| `.claude/skills/improve/SKILL.md` | generic | The project name. |
| `.claude/skills/roadmap/SKILL.md` | specific | The three goals of aoe2mc. |
| `docs/OPERATOR.md` | generic | None (NAME is the name of `repo` in `agent.toml`). |
| `.claude/skills/human/SKILL.md` | specific | The preparation of a play test (worlds, `game/run.py`, Minecraft 26.3). |
| `.claude/skills/demo/SKILL.md` | specific | The demo game (`--random-map arabia`, `game/run.py`, `game/demo_watch.py`, the Minecraft client folders of macOS). |
| `.claude/settings.json` | generic | The permission rules name the repository (they cannot read `agent.toml`). |
| `.claude/hooks/session-start.sh` | generic | The Python packages and the setup version file name. |
| `.claude/hooks/guard-main.sh` | generic | None. |
| `.claude/hooks/guard-shell.sh` | generic | None. |
| `scripts/cloud-setup.sh` | specific | Java, the Minecraft server jars, the Vulkan and X tools of the client. |
| `scripts/allowed-domains.txt` | specific | The "Allowed domains" of the cloud environment: the hosts of the tests and the research tools. |
| `scripts/autopilot.sh` | generic | None (runs on the owner's computer). |
| `tools/agent_config.py` | generic | None (reads `agent.toml`). |
| `tools/bootstrap.py` | generic | None (sets up this system in a new repository, #906). |
| `tools/claim.py` | generic | None (`agent.toml`). |
| `tools/usage.py` | generic | None. |
| `tools/dashboard_site.py` | specific | The owner's dashboard page and its runtime (GitHub Pages). |
| `tools/pacer.py` | generic | None (the API triggers come from the secrets of `pacer.yml`, #3193). |
| `tools/dashboard.py` | generic | None (`agent.toml`). |
| `tools/feedback.py` | generic | None (`agent.toml`). |
| `tools/health.py` | generic | None (`agent.toml`). |
| `tools/metrics_log.py` | generic | None (the log of the status issue comments on the branch `metrics`, #1983). |
| `tools/report.py` | generic | None (the run report of step 8; the release bar only with a project `tools/release.py`, #1963). |
| `tools/ticket_context.py` | generic | None (the code places that a ticket body names, #3829). |
| `tools/tokens.py` | generic | None. |
| `tools/operator_check.py` | generic | None (`agent.toml`). |
| `tools/owner_tasks.py` | generic | None (`agent.toml`). |
| `tools/unconflict.py` | generic | None (solves add-add conflicts for `unconflict.yml`, #1864). |
| `tools/unconflict_pick.py` | generic | None (the PRs of `unconflict.yml`, with git and few API calls). |
| `tools/merge_main.py` | generic | None (merges `main` into a branch in one call: solve, commit, check, push). |
| `tools/cycle_start.py` | generic | None (steps 1 to 5 of the autopilot skill in one call). |
| `tools/ship_pr.py` | generic | None (checks, commit, guard, push and PR of a ticket in one call). |
| `tools/merge_jsonl.py` | generic | None (the merge driver `merge=jsonl`: JSON lines by "name", a line that both sides changed by key and list item, #2004, #2064). |
| `tests/test_agent_config.py` | generic | None (a test of `tools/agent_config.py`). |
| `tests/test_claim.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_active_pr.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_code_span.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_conflict.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_exit.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_first.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_refill.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_release_label.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_refill_all_closed.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_revived.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_claim_takeover.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_dashboard.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_deep_lane.py` | generic | None (a test of `tools/usage.py`, `tools/claim.py` and `tools/dashboard.py`). |
| `tests/test_dashboard_claimed.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_decide.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_fresh.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_muted.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_overlap.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_process.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_start.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_start_bad.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_dashboard_start_prs.py` | generic | None (a test of `tools/dashboard.py`). |
| `tests/test_feedback.py` | generic | None (a test of `tools/feedback.py`). |
| `tests/test_feedback_gap.py` | generic | None (a test of `tools/feedback.py`). |
| `tests/test_feedback_quote.py` | generic | None (a test of `tools/feedback.py`). |
| `tests/test_health.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_compare.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_conflicts.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_pr.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_reviews.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_takeovers.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_health_misses.py` | generic | None (a test of `tools/health.py`). |
| `tests/test_owner_work.py` | generic | None (a test of `tools/dashboard.py`, `tools/claim.py`, `tools/cycle_start.py` and `tools/health.py`: the owner work, owner 2026-10-29). |
| `tests/test_review_gap.py` | generic | None (a test of `tools/claim.py`). |
| `tests/test_health_until_pages.py` | generic | None (a test of `tools/health.py`, #3072). |
| `tests/test_operator.py` | generic | None (a test of `tools/operator_check.py`). |
| `tests/test_owner_tasks.py` | generic | None (a test of `tools/owner_tasks.py`). |
| `tests/test_owner_tasks_close.py` | generic | None (a test of `tools/owner_tasks.py`). |
| `tests/test_owner_tasks_project.py` | generic | None (a test of `tools/owner_tasks.py`). |
| `tests/test_owner_tasks_wait.py` | generic | None (a test of `tools/owner_tasks.py`). |
| `tests/test_report.py` | generic | None (a test of `tools/report.py`). |
| `tests/test_tokens.py` | generic | None (a test of `tools/tokens.py`). |
| `tests/test_tokens_verify.py` | generic | None (a test of `tools/tokens.py`). |
| `tests/test_tokens_cost.py` | generic | None (a test of `tools/tokens.py`). |
| `tests/test_tokens_phases.py` | generic | None (a test of `tools/tokens.py`). |
| `tests/test_run_data.py` | generic | None (a test of `tools/tokens.py`, `tools/pacer.py` and `tools/metrics_log.py`). |
| `tests/test_unconflict.py` | generic | None (a test of `tools/unconflict.py`). |
| `tests/test_automerge_failure.py` | generic | None (a test of `.github/workflows/automerge.yml`). |
| `tests/test_unconflict_no_markers.py` | generic | None (a test of `tools/unconflict.py`, #3062). |
| `tests/test_unconflict_pick.py` | generic | None (a test of `tools/unconflict_pick.py`). |
| `tests/test_merge_main.py` | generic | None (a test of `tools/merge_main.py`). |
| `tests/test_cycle_start.py` | generic | None (a test of `tools/cycle_start.py`). |
| `tests/test_ship_pr.py` | generic | None (a test of `tools/ship_pr.py`). |
| `tests/test_merge_jsonl.py` | generic | None (a test of `tools/merge_jsonl.py`). |
| `tests/test_merge_jsonl_order.py` | generic | None (a test of `tools/merge_jsonl.py`: the line order of a move, #3065). |
| `tests/test_pacer.py` | generic | None (a test of `tools/usage.py`). |
| `tests/test_dashboard_site.py` | specific | None (a test of `tools/dashboard_site.py`). |
| `tests/test_pacer_script.py` | generic | None (a test of `tools/pacer.py`). |
| `tests/test_usage.py` | generic | None (a test of `tools/usage.py`). |
| `tests/test_usage_status_once.py` | generic | None (a test of `tools/usage.py`). |
| `tests/test_usage_week.py` | generic | None (a test of `tools/usage.py`). |
| `tests/test_generic_tools.py` | specific | The tools of aoe2mc that generic files may name (`OPTIONAL`, #1963). |
| `tests/test_generic_words.py` | specific | The words of aoe2mc that the generic files must not contain (#1900). |
| `.github/workflows/ci.yml` | specific | The Python, Java and Minecraft steps, the test markers. The red-`main` ticket is generic. |
| `.github/workflows/automerge.yml` | generic | The branch prefixes `claude/*`, `agent/*` and `ccr-*` (#3382). |
| `.github/workflows/unconflict.yml` | generic | None. |
| `.github/workflows/claims.yml` | generic | None. |
| `.github/workflows/close.yml` | generic | None. It closes the issues with the label `close` (#1740). |
| `.github/workflows/dashboard.yml` | generic | None. |
| `.github/workflows/dashboard-site.yml` | specific | The owner's dashboard page on GitHub Pages (`tools/dashboard_site.py`, `tools/dashboard_artifact/`). |
| `.github/workflows/pacer.yml` | generic | The secrets of the API triggers, one pair per lane (#3193). |
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
