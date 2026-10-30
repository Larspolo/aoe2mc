# Several collaborators at the same time (plan, #4185)

This plan lets more than one person work on the project at the same time, each with an own Claude account. It
adds each account to the pacer automatically, and it checks the quota of each account separately. It assumes that
all collaborators are fair. The parts of the system are in `framework/docs/SYSTEM.md`; this document names only what changes.

Status: a plan. Epic #4232 does it. Decision #4229 (who steers): A, all collaborators steer, `owner` is the tie-breaker
(owner, 2026-10-29). The other parts have one clearly best form, named below with the reason.

## What assumes one person today

| Place | Assumption | Effect with two collaborators |
|---|---|---|
| `agent.toml` `owner`, `framework/tools/feedback.py` `by_owner`, `framework/tools/health.py` `OWNER`, `CLAUDE.md`, `framework/docs/STEERING.md` | One GitHub login gives instructions | The comments of the second person are data, not instructions |
| `pacer.yml` secrets `CLAUDE_CODE_OAUTH_TOKEN`, `PACER_URL_<TASK>`, `PACER_TOKEN_<TASK>` | One account: one quota read, one set of scheduled tasks | The pacer cannot read or fire a second account |
| `framework/tools/usage.py` `target_runs`, `fire` | One 5-hour and one 7-day window for all runs | Runs of account B count against the windows of account A |
| `framework/tools/health.py` `measured_burn`, `measured_burn7` | All `Usage:` lines come from one account | The burn per run mixes two quotas and is wrong for both |
| `framework/tools/claim.py` claims, the `Usage:` and `Run:` lines | A run has a lane, no account | No tool can count the runs or the PRs of one account |
| A run's own `usage.py --fire` (autopilot step 1, `scheduled` step 3) | The run's quota is the quota of all runs | A run of account B stops when account A is full |
| `needs-human` tickets, `framework/tools/owner_tasks.py`, the `human` skill | One person does the owner tasks | The tasks of a setup step go to the wrong person |
| `framework/docs/OPERATOR.md` section 4 | A move from one account to another, never two at once | No steps to add an account |

What does not change: the tickets, the claim locks (git refs work for any run), Automerge, Unconflict, CI, the
review and refill locks, the merge drivers. They already work for any number of runs.

## The plan

### 1. Accounts are data (`agent.toml`)

A new table per account. The name is short and upper-case safe, because it is part of the secret names.

```toml
[accounts.lars]                  # the first account: the present secrets, no suffix
login = "Larspolo"               # the GitHub login of the collaborator
[accounts.bob]
login = "bob-example"
reserve = 0.2                    # optional: leave 20 % of each window for the collaborator's own Claude work
```

`reserve` (default 0) lowers the aim of `usage.target_runs` for that account only (P7: use the whole quota is the
default; a collaborator who also works by hand keeps a part). Who steers: decision #4229 chose A (2026-10-29): a list `owners` (default: `owner`) that `framework/tools/feedback.py` and `framework/tools/health.py` read, and
Automerge holds each PR that changes `owners` or `[accounts]` until an owner approves it.

### 2. Each run knows its account

Each collaborator makes an own cloud environment (`framework/docs/SYSTEM.md`, setup step 2) and sets the environment variable
`AGENT_ACCOUNT=<name>` there. The SessionStart hook copies it to `git config aoe2mc.account`, as the lane today.
`framework/tools/claim.py` writes it into each claim (`... account bob lane deep`: the lane stays at the end, where its readers
look), and `framework/tools/usage.py` and `framework/tools/report.py` write it into the `Usage:` and `Run:` lines (`· account bob`). With no variable, the run belongs to the first
account (the present runs keep working with no change).
Why the environment and not the task prompt: the environment is per account already, it also covers a collaborator's
own sessions, and the prompt stays `/scheduled ARGUMENT` (owner, 2026-10-29).

### 3. The pacer reads and fires each account

Done in #4237 (`framework/tools/pacer.py` `accounts`, `account_targets`, `assign`).

- Secrets: the first account keeps the present names. Each other account adds `CLAUDE_CODE_OAUTH_TOKEN_<NAME>`,
  `PACER_URL_<NAME>_<TASK>` and `PACER_TOKEN_<NAME>_<TASK>` (`<TASK>` = `MAIN`, `HAIKU`, `DEEP`).
- `pacer.yml` reads the secrets one by one, by name (2026-10-30). Its first job prints the names of the secrets of
  each table of `[accounts]` in `agent.toml` and each task (`framework/tools/pacer.py --secrets`, `secret_names`). The pacer job
  gets the value of name i as `SECRET_<i>` (`secrets[...]` of the name), and `framework/tools/pacer.py` finds the accounts by
  these names. So a new collaborator adds secrets and a table in `agent.toml`, and nothing else in the workflow: the
  pacer uses the account at its next loop (automatic scaling). The workflow has 35 slots: the first account and 4 more.
  Do not give the step `toJSON(secrets)`: GitHub held the runs that did it as "may be malicious".
- `framework/tools/usage.py read_usage(token)`: one tiny CLI call per account, with that account's token in the environment of
  the call (about 1 s each).
- Per account: its own target (`target_runs` with its own usage, `reserve`, 5-hour and 7-day burns, `week_guard`) and
  its own claims (the beating claims with its account tag). Its missing runs: target − claims.
- Shared limits stay global, because they protect the repository, not a quota: `max_runs`, `max_fire`, the flow
  brake (`max_waiting_prs`, `max_ci_queue`), the ready tickets plus `refill_runs`, the API rate limit of GitHub.
- Each cycle: K = the minimum of the sum of the missing runs and the global limits. The pacer gives the K runs to the
  accounts in order of their missing runs (the most first, one at a time), so the account with the most free quota
  starts the most runs. Each account keeps its own fallback from a lane task to its main task (HTTP 429 today).
- A failed quota read of one account starts no runs on that account and does not stop the others (the cycle record
  names the account).

### 4. Usage per account is measured and shown

- `framework/tools/health.py`: the burns from the pairs of `Usage:` lines of one account only. A new account uses `BURN` and
  `BURN7` until it has 5 pairs.
- A run's own `usage.py --fire` reads its own account (the CLI in a run uses the run's account) and compares it with
  the claims of its own account.
- The pacer record (`pacer.py --log`) and the dashboard (`framework/tools/dashboard.py`, `tools/dashboard_site.py`) show per
  account: 5-hour and 7-day usage, the target, the runs, the merged PRs and the tokens per merged PR.

### 5. Add a collaborator

A new section of `framework/docs/OPERATOR.md` ("Add a collaborator"), next to section 4 (move to another account), with a
check in `framework/tools/operator_check.py`:
1. The owner adds the GitHub login as a collaborator with write access. The collaborator connects GitHub in the
   Claude app (the Claude GitHub app is already on the repository).
2. The collaborator makes the cloud environment (setup script, allowed domains) with `AGENT_ACCOUNT=<name>`.
3. The collaborator makes the scheduled tasks "aoe2mc autopilot", "... haiku", "... deep" with their API triggers
   (`framework/docs/OPERATOR.md`, section 3), and runs `claude setup-token`.
4. The owner adds the secrets of step 3 to the repository, and a PR adds `[accounts.<name>]`.
5. `python3 framework/tools/operator_check.py` reads the quota of each account and does a dry run of the pacer.

A `needs-human` ticket for one environment (a new setup script, a new host) mentions the login of that account, not
only the owner: the run knows its account (part 2).

## Limits that do not scale with accounts

More accounts give more runs, but these stay the same and become the bottleneck: the CI runners of the repository
(the flow brake stops new runs at `max_ci_queue`), merge conflicts between parallel PRs (more runs, more conflicts),
the ready tickets (the refill must keep up: `refill_runs`), and the REST budget of the workflow token for the
dashboards (the runs use the GitHub token of their own collaborator, so the runs scale). `framework/tools/health.py` already
measures each of them; the `improve` skill raises `max_runs` only when they allow it.
