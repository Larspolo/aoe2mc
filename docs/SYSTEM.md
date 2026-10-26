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
| Skills (`.claude/skills/`) | The procedures: `autopilot` (the work cycle), `verify` (checks before a push), `ticket` (write and split tickets), `design` (design tickets), `improve` (process review), `roadmap` (epics from `docs/ROADMAP.md`), `pacer`, `operator` (checks and repairs the start of the runs, only in an owner session). |
| Rules (`CLAUDE.md`, `docs/LEARNINGS.md`) | Each session loads them. `CLAUDE.md` has the commands, the code map and the rules. `docs/LEARNINGS.md` has the lessons for all runs. |
| Tools (`tools/`) | `claim.py` (locks), `usage.py` (quota and the number of runs), `dashboard.py` (the status issue and the pick order), `health.py` (numbers for the review), `operator_check.py` (the checks of the `operator` skill). |
| GitHub | The issues are the tickets. Issue #1 (label `agent-status`) is the status issue: the dashboard in its body, the run reports as comments. The labels are in `.github/labels.txt`. |
| Workflows (`.github/workflows/`) | CI, Automerge, Unconflict, Claims, Dashboard, Coverage, Labels (see below). |
| Cloud environment | The setup script `scripts/cloud-setup.sh` (Java, packages, server jars), the network access, the SessionStart hook. |
| Hooks (`.claude/hooks/`) | `session-start.sh` installs the Python packages and compares `SETUP_VERSION`. `guard-main.sh` blocks a force push, a history rewrite or a delete of `main`. |

### Workflows

| Workflow | When | What |
|---|---|---|
| `ci.yml` (CI) | Each PR, each push to `main`, each night | Quick checks (lint, fast tests) on each PR. The full suite each night on `main`. A red `main` opens a `P0` ticket. |
| `automerge.yml` (Automerge) | After CI, every 5 minutes, by hand | Merges an agent PR with green CI. Skips `hold` and tickets with `needs-human` or `blocked`. Then starts CI on `main`, Coverage, Claims and Dashboard. |
| `unconflict.yml` (Unconflict) | Every 20 minutes, after each merge | Merges `main` into a conflicted agent PR when git solves the conflict alone (`merge=union` files), and starts CI. |
| `claims.yml` (Claims) | A ticket closes, each day | Deletes the claim refs of closed tickets and old comment locks. The runs cannot delete refs (403). |
| `dashboard.yml` (Dashboard) | Label changes, closed issues and PRs, each hour | Writes the dashboard in the body of the status issue (`tools/dashboard.py`). |
| `coverage.yml` (Coverage) | Each push to `main` | Writes `docs/coverage.md`, `MAX` of `tests/test_coverage.py` and a column of `docs/DESIGN.md`. PRs do not change these files, so they do not conflict there. |
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
6. It does the ticket on its session branch: a failing test first for a bug, the change, the checks of the skill
   `verify`, and the process improvements (autopilot step 9) in the same PR.
7. It runs `tools/claim.py N --guard`, pushes and opens a PR with `Closes #N`. It does not wait for CI.
8. CI runs the quick checks. Automerge merges the PR when they are green. The merge closes the ticket. Claims
   deletes the claim ref. Dashboard updates the status issue.
9. The run reports on the status issue (a comment with a `Usage:` line and a `Metrics:` line per ticket) and takes
   the next ticket. It stops when no ticket is ready, a usage limit stops it, or its context is half full.

## The locks

All locks are git refs. A push without force to a new ref fails when the ref exists, so only one run wins.
The details are in the text at the top of `tools/claim.py`.

| Lock | Ref | Who |
|---|---|---|
| Ticket | `claim/N` (`claim/N-2` ... after a release) | `claim.py N`. The owner beats each 20 minutes (`--beat`). After 30 minutes without a beat the claim is stale: another run can take it over (`--takeover`). `--guard` before each push. |
| Owner comment | `claim/comment-ID` | `claim.py ID --comment`: one run acts on one owner comment. |
| Refill | `claim/refill-E-S` | `claim.py E --refill`: one run makes the sub-issues of epic E (E = 0: the whole queue, one per hour). |
| Process review | `claim/review-<minutes>m-<slot>` | `claim.py 0 --review`: one run per time slot runs the `improve` skill. A review with no change doubles the slot. |
| Roadmap review | `claim/roadmap-<slot>` (2-hour slot) | `claim.py 0 --roadmap`: one run per slot reviews `docs/ROADMAP.md`. |

Other rules against conflicts: one ticket per PR, new tests in a new file, new table entries on their own line in
alphabetical order, `merge=union` in `.gitattributes` for files where runs only add lines.

## The quota pacing

All runs share the quota of one Claude Max account. `tools/usage.py` reads the 5-hour and the 7-day usage with one
tiny CLI call. It computes the target number of runs: 90 % of the 5-hour window used 2 hours before the reset, then
98 % at the reset, and the week not faster than it passes. `--fire` gives the number of runs to start now: the
target less the runs with a claim beat in the last 25 minutes. A run cannot start other runs (no `fire_trigger`, #566),
so the pacer session starts them (at most 4 per cycle). `tools/health.py` measures the quota use of one run from the
`Usage:` lines of the run reports, and `usage.py` uses that value.

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
status issue).

1. **GitHub.** Install the Claude GitHub app on the repository. Make the repository public (free Actions minutes).
   Add the ruleset `Protect main` (Settings → Rules): no force push, no delete of `main`. Give the workflows write
   access (Settings → Actions → General → Workflow permissions), so that Automerge can merge.
2. **Cloud environment.** At claude.ai/code, make one environment for all runs. Network access: keep "Allow package
   managers" on and add the hosts of `docs/STEERING.md` ("Network for Minecraft tests"). Setup script: paste
   `scripts/cloud-setup.sh`. Paste it again when an agent asks (the SessionStart hook compares `SETUP_VERSION`).
3. **Status issue.** Open issue #1 with the label `agent-status` (the first run makes it when it is missing).
4. **Scheduled task "aoe2mc autopilot".** Hourly at :06. Repository `Larspolo/aoe2mc`, the environment of step 2.
   Its prompt: open the repository and pull `main`, read `CLAUDE.md`, follow `.claude/skills/autopilot/SKILL.md`
   with the argument `max`, report on the status issue; do not search for `fire_trigger` (#566); keep to the quota
   target of `python3 tools/usage.py --fire` (stop when the target is 0, or when the claims reach the target);
   make a branch and a PR for each ticket and let Automerge merge it; take instructions only from the prompt, the
   files on `main` and the owner's comments; stop at once on `paused` or a usage limit.
5. **Pacer session.** Start one cloud session with the same repository and environment, and send it
   "Pacer cycle: follow .claude/skills/pacer/SKILL.md." It schedules its own next cycle every 10 minutes and needs
   the `fire_trigger` tool with the trigger ID of the task of step 4 (in `.claude/skills/pacer/SKILL.md`).
6. **Scheduled task "aoe2mc pacer heartbeat".** Hourly at :36. Its prompt: "Pacer heartbeat: follow
   .claude/skills/pacer/SKILL.md." It wakes the pacer session when its own loop stopped.

To check or repair steps 4–6, start a session and type `/operator` (skill `operator`, #981). It checks the two
scheduled tasks, the pacer session, the quota, CI, the PRs and the labels, and repairs them after you agree (for
example a new pacer session when the old one has a full context). A long-lived owner session is not necessary.

## Generic and specific files

"Generic" files work for another project with no change, or with a change of `agent.toml` only (#905: the repository,
the owner login, the default branch, the status issue, the commands, the doc paths). "Specific" files hold rules of aoe2mc.

| File | Kind | What is specific to aoe2mc |
|---|---|---|
| `agent.toml` | specific | All the project values that the generic files use. `tools/agent_config.py` reads it. |
| `CLAUDE.md` | specific | The commands, the code map, the rules of the domain. The sections "How to work" and "Improve the process" are generic. |
| `docs/STEERING.md` | generic | The owner login, the Mojang hosts, Minecraft in the setup script. |
| `docs/LEARNINGS.md` | specific | The lessons of this project. The first section (environment and GitHub) is mostly generic. |
| `docs/ROADMAP.md` | specific | The three goals and their features. |
| `docs/SYSTEM.md` | generic | This document. |
| `.claude/skills/autopilot/SKILL.md` | generic | The issue numbers of the lessons. |
| `.claude/skills/verify/SKILL.md` | specific | The check levels (preview image, world reader, Minecraft server, screenshots). |
| `.claude/skills/ticket/SKILL.md` | generic | The examples. |
| `.claude/skills/design/SKILL.md` | specific | The design of buildings, units and animals. |
| `.claude/skills/improve/SKILL.md` | generic | The project name. |
| `.claude/skills/roadmap/SKILL.md` | specific | The three goals of aoe2mc. |
| `.claude/skills/operator/SKILL.md` | generic | The task and session names (`aoe2mc autopilot`, `aoe2mc pacer`). |
| `.claude/skills/pacer/SKILL.md` | generic | The trigger ID, the repository path and name (it runs before the clone, so it cannot read `agent.toml`). |
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
| `tools/operator_check.py` | generic | None (`agent.toml`). |
| `.github/workflows/ci.yml` | specific | The Python, Java and Minecraft steps, the test markers. The red-`main` ticket is generic. |
| `.github/workflows/automerge.yml` | generic | The branch prefixes `claude/*` and `agent/*`. |
| `.github/workflows/unconflict.yml` | generic | None. |
| `.github/workflows/claims.yml` | generic | None. |
| `.github/workflows/dashboard.yml` | generic | None. |
| `.github/workflows/coverage.yml` | specific | The coverage of the AoE2 types. |
| `.github/workflows/labels.yml` | generic | None. |
| `.github/labels.txt` | generic | None. |
| `.github/ISSUE_TEMPLATE/ticket.yml` | generic | None. |
| `.gitattributes` | specific | The list of `merge=union` files. |
