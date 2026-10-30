---
name: new-project
description: Set up a new project with this agent system from a short project idea. Ask the owner only what you cannot decide, suggest the stack, the tools and the roadmap (goals, features and their sub-items), fill the template, and make and set up the GitHub repository with scripts. Use when the owner says "new project", "start a project" or "/new-project". Argument - the project idea (optional).
---

# Set up a new project

The goal: the owner gives an idea and a few answers, you do all other work. The owner does only the steps that need
the owner's own accounts (step 7). Write all text in ASD-STE100 Simplified Technical English. The manual form of
these steps: `framework/docs/NEW_PROJECT.md`.

**Rules for the questions**
- Ask only what changes the result and what you cannot find or decide yourself. Never ask for a tool, a linter, a
  test runner, a file layout or a label: suggest the best one and say why in one line.
- Ask with AskUserQuestion, at most 4 questions in one call. Put your suggestion first, with "(Recommended)".
- Ask each thing once. Keep each answer for the next steps.

## 1. Check the place

1. Run `gh auth status`. With a login, the scripts of step 6 do all GitHub work. With no login (a cloud session), use
   the cloud way of step 6.
2. Get the owner login: `gh api user --jq .login`, else `mcp__github__get_me`.

## 2. Get the idea

When the argument has no project idea, ask the owner in one message: "Describe the project in 3 to 5 sentences: what
it does, for whom, and what is done when it works." Do not continue without the idea.

From the idea, find these values yourself: the project kind (library, CLI, web app, game, data pipeline, ...), the
language, the users, the main inputs and outputs, and the hard parts.

## 3. Suggest the stack

Select the stack from the idea. Use the standard tools of the language, not the newest ones:

| Language | Lint | Fast tests | Install |
|---|---|---|---|
| Python | `ruff check .` | `python3 -m pytest -n auto` | `python3 -m pip install -r requirements-dev.txt` |
| TypeScript or JavaScript | `npx @biomejs/biome check .` | `npx vitest run` | `npm ci` |
| Rust | `cargo clippy -- -D warnings` | `cargo test` | `cargo fetch` |
| Go | `go vet ./...` | `go test ./...` | `go mod download` |
| Java or Kotlin | `./gradlew check -x test` | `./gradlew test` | `./gradlew dependencies` |

- The agent tools are Python, so each project also needs Python 3.12, `ruff` and `pytest` (the template has them).
  For another language, the commands run both: `ruff check . && <lint>`, `python3 -m pytest -q && <tests>`.
- Select Python when the idea names no language and Python can do the job.
- A slow test level (`slow` in `agent.toml`) only when the project has slow checks (a browser, a server, a big data set).

Ask in one AskUserQuestion call (skip a question when the idea answers it):
1. "Repository": `OWNER/<a short name from the idea>` (Recommended), and one other name.
2. "Stack": your stack, with the lint and test tools in the description (Recommended), and one other good stack.
3. "Visibility": public (Recommended: free Actions minutes), private.

## 4. Suggest the roadmap

Write a draft of `steering/project/ROADMAP.md` yourself. The runs make all epics and tickets from it, so it must
describe the whole product:

- 2 to 4 goals. A goal is a result for the user ("Convert a map", "Play a game"), not a layer of the code.
- 4 to 8 features per goal, in the order to build them. The first feature of goal 1 is the smallest version that runs
  from start to end (a walking skeleton).
- Each feature: `- [ ] \`goal:feature\` text`, with a short key in lower case (`convert:terrain`), and 1 to 3
  sub-items under it (`  - text`): what the user can do or see when the feature is done. A sub-item is a check,
  not a task.
- Keep the head of the template file (the text above `## 1.`).

Show the draft in the chat. Then ask with AskUserQuestion: "Roadmap": "Use it" (Recommended), "Change some items"
(the owner writes the changes), "More features", "Fewer features". Change the draft and ask again, until the owner
selects "Use it".

## 5. Fill the project

1. `python3 framework/tools/bootstrap.py DIR --repo OWNER/NAME`, with DIR a new directory in the scratchpad.
2. Fill each start file in DIR (each `TODO` line). Do not leave a `TODO`:
   - `steering/project/ROADMAP.md`: the roadmap of step 4.
   - `agent.toml`: the commands of step 3 in `[commands]`. Keep the other values.
   - `CLAUDE.md`: the idea in two sentences, the commands table, the planned code map (the directories of the stack).
   - `.claude/skills/verify/SKILL.md`: level 1 lint and fast tests, then the levels of the stack (slow tests, a run of
     the program, a screenshot for a user interface).
   - `.github/workflows/ci.yml`: the setup step of the language next to `setup-python`. Keep the job name `quick`.
   - `scripts/cloud-setup.sh`: the install of the stack, in `SETUP_NEEDS` too. `scripts/allowed-domains.txt`: the
     package hosts of the stack. `docs/ENVIRONMENT.md`: both in words.
   - `pyproject.toml`, `requirements-dev.txt`: keep them. For another language, add its project file (`package.json`,
     `Cargo.toml`, ...) with the lint and test tools, and one smoke test of the language.
   - `steering/project/PRINCIPLES.md`: keep it empty.
3. In DIR, run the install, lint and fast test commands. All must pass before step 6. Fix the files, not the tests.

## 6. Make the repository

**With `gh` (a local session):**

1. `python3 framework/tools/new_repo.py DIR --repo OWNER/NAME --description "<one line>" --dry-run`, then the same
   without `--dry-run` (`--private` when the owner selected it). The tool makes the first commit, the repository,
   the push, the workflow permissions, the ruleset `Protect main`, the labels and the status issue.
2. Read each `FAIL` line. Fix the cause and run the tool again: it skips the steps that are done.

**With no `gh` (a cloud session):**

1. Make the repository with `mcp__github__create_repository` (the name, the description, `private` of step 3).
2. Ask the owner to install the Claude GitHub app on the new repository (step 7, item 1) and wait for the answer.
   Then add the repository to the session with `add_repo`, and push DIR: `git -C DIR init -b main`, commit, add the
   remote, `git push -u origin main`.
3. The settings, labels and status issue need `gh`: give the owner the command of the local way, item 1. The first
   run of the agents also makes the status issue when it is missing.

## 7. The steps of the owner

Give the owner one numbered list with only these steps, with the real repository name in each line:

1. Install the Claude GitHub app on the repository: https://github.com/apps/claude/installations/select_target.
2. At claude.ai/code, make a cloud environment: "Allow package managers" on, the whole file
   `scripts/allowed-domains.txt` as the allowed domains, the whole file `scripts/cloud-setup.sh` as the setup script.
   Show both files in the chat, ready to copy.
3. Make the scheduled task "NAME autopilot": the repository, the environment of item 2, no schedule, the prompt
   `/scheduled max`, Opus at effort low. Add an API trigger, and keep its fire URL and token. The same for each lane
   of `weights` in `steering/system/system.toml` ("NAME autopilot haiku": Haiku, the prompt `/scheduled max lane haiku`).
   When the session has a tool that makes scheduled tasks, make them yourself and give the owner only the API triggers.
4. Run `claude setup-token` on your computer.
5. Type `! python3 framework/tools/new_repo.py DIR --repo OWNER/NAME --secrets` in this session. The tool asks for
   the token of item 4 and the URL and token of each task, with no echo. In a cloud session: add each secret of
   `python3 framework/tools/new_repo.py DIR --repo OWNER/NAME --dry-run --secrets` at GitHub → Settings → Secrets and
   variables → Actions. Never ask for a secret in the chat.
6. Give me the ID of the task "NAME autopilot".

When the owner gives the ID, write it to `trigger` in `[pacing]` of `DIR/steering/system/system.toml`, commit,
push to the default branch, and run `python3 framework/tools/new_repo.py DIR --repo OWNER/NAME --start`.

## 8. Check and report

1. `gh run list --repo OWNER/NAME --limit 5`: CI and Pacer start.
2. Tell the owner: the repository URL, the roadmap goals, the stack, and what the first run does (it makes the
   epics and the tickets from the roadmap). The owner steers through issues from then on
   (`framework/docs/STEERING.md`).
