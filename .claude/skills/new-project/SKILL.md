---
name: new-project
description: Set up a new project with this agent system from a short project idea. Ask the owner only what you cannot decide, suggest the stack, the tools and the roadmap (goals, features and their sub-items), fill the template, and make and set up the GitHub repository with scripts. Use when the owner says "new project", "start a project" or "/new-project". Argument - the project idea (optional).
---

# Set up a new project

The goal: the owner gives an idea and a few answers, you do all other work. The owner does only the steps that need
the owner's own accounts (step 8). Write all text in ASD-STE100 Simplified Technical English. The manual form of
these steps: `framework/docs/NEW_PROJECT.md`.

**Rules for the questions**
- Ask only what changes the result and what you cannot find or decide yourself. Never ask for a tool, a linter, a
  test runner, a file layout or a label: suggest the best one and say why in one line.
- Ask with AskUserQuestion, at most 4 questions in one call. Put your suggestion first, with "(Recommended)".
- Ask each thing once. Keep each answer for the next steps.

## 1. Check the place

1. Run `gh auth status`. With a login (a local session), the scripts of step 7 do all GitHub work. With no login (a
   cloud session), use the cloud way of step 7.
2. Get the owner login: `gh api user --jq .login`, else `mcp__github__get_me`.
3. Know your limits: `.claude/settings.json` denies the session tools of scheduled tasks and repositories
   (`mcp__claude-code-remote`). You cannot make a scheduled task, an API trigger, a cloud environment or a secret
   value. The owner does these steps, and you guide each one (step 8).

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

Then ask for the resources of the owner in a second AskUserQuestion call. The answers decide what the agents can
plan, and how the owner can try a feature (step 4):

1. "Computer": macOS, Windows, Linux, "Only a phone or a tablet". With a computer, the project gets a development
   server that the owner starts with `/try`.
2. "Accounts and devices" (multiSelect, from the idea): what the project needs and the owner may have, for example
   a license of a program or a game, a test device (a phone, a console), a hosting account, an API key of a paid
   service. Add "None of these".
3. "Budget" for services: "Free only (Recommended)", "Up to 10 USD a month", "More". With "Free only", a service with
   a cost always gets a decision ticket.
4. "Runs" (the Claude plan): "One main task (Recommended)": one scheduled task, 3 secrets. "Main and a haiku lane":
   small tickets on a cheap model, one task more. "Main, haiku and deep lanes": for a big plan, two tasks more.

## 4. Ask the direction

The runs work for months with no owner in the session. These answers tell them what the owner wants. Ask them in
one AskUserQuestion call, with options that you make from the idea (not general words):

1. **"Philosophy"** (one or two questions): find the main tension of the project, where two good goals pull apart,
   and ask which side wins. Examples: a port of a game to another platform ("the rules of the game, the look and the
   controls of the platform" against "all as in the original"), a tool ("few options that work at once" against
   "each option of the expert"), a model ("fast and close" against "slow and exact"). Make 2 or 3 options per
   tension; recommend the one that fits the idea best. Also ask, or decide with a reason: use the features of the
   platform or library first, or own code.
2. **"Your decisions"** (multiSelect): the areas where the owner decides each choice, also when one option is
   clearly best. Suggest areas of this project, for example: the look and the user interface, the rules or the
   behavior that a user sees, the order of the features, a new dependency or a service with a cost, the architecture.
   Add "Only real ties (Recommended)": the agents decide, and ask only when two options are equally good.
3. **"Try a feature"** (multiSelect): how the owner tries a new feature. An image does not show an interaction (a
   click, an input, a game, a flow of pages). Recommend a development server for each project with interaction, when
   the owner has a computer. Suggest what fits the project kind and the resources:
   - "Development server (`/try`)": one command (`dev` in `[commands]`) starts the project on the owner's computer.
     The owner types `/try` in a local session: it starts the server at the newest main, lists what is new with steps
     to try it, and makes a ticket for each feedback.
   - "Images in each PR": screenshots, a short recording or the output of a run; no work for the owner.
   - "A test ticket at the end of each epic": a `needs-human` ticket with the steps to try the feature.
   - "A build to download": each epic makes a release (a file, a package, an installer) that the owner runs.
   - "A live preview": each PR or epic gets a preview URL (web projects, and only with a hosting account).

Write the answers in step 6. When an answer is "Other", use the owner's words.

## 5. Suggest the roadmap

Write a draft of `steering/project/ROADMAP.md` yourself. The runs make all epics and tickets from it, so it must
describe the whole product:

- 2 to 4 goals. A goal is a result for the user ("Convert a map", "Play a game"), not a layer of the code.
- 4 to 8 features per goal, in the order to build them. The first feature of goal 1 is the smallest version that runs
  from start to end (a walking skeleton).
- Each feature: `- [ ] \`goal:feature\` text`, with a short key in lower case (`convert:terrain`), and 1 to 3
  sub-items under it (`  - text`): what the user can do or see when the feature is done. A sub-item is a check,
  not a task.
- Follow the philosophy of step 4: a feature that goes against it is not on the roadmap. When the owner tries
  features with a test ticket or a build, make each epic end with a result that the owner can try.
- Keep the head of the template file (the text above `## 1.`).

Show the draft in the chat. Then ask with AskUserQuestion: "Roadmap": "Use it" (Recommended), "Change some items"
(the owner writes the changes), "More features", "Fewer features". Change the draft and ask again, until the owner
selects "Use it".

## 6. Fill the project

1. `python3 framework/tools/bootstrap.py DIR --repo OWNER/NAME`, with DIR a new directory in the scratchpad.
2. Fill each start file in DIR (each `TODO` line). Do not leave a `TODO`:
   - `steering/project/ROADMAP.md`: the roadmap of step 5.
   - `agent.toml`: the commands of step 3 in `[commands]`. Keep the other values.
   - `CLAUDE.md`: the idea in two sentences, the commands table, the planned code map (the directories of the stack).
   - `.claude/skills/verify/SKILL.md`: level 1 lint and fast tests, then the levels of the stack (slow tests, a run of
     the program, a screenshot for a user interface).
   - `.github/workflows/ci.yml`: the setup step of the language next to `setup-python`. Keep the job name `quick`.
   - `scripts/cloud-setup.sh`: the install of the stack, in `SETUP_NEEDS` too. `scripts/allowed-domains.txt`: the
     package hosts of the stack. `docs/ENVIRONMENT.md`: both in words.
   - `pyproject.toml`, `requirements-dev.txt`: keep them. For another language, add its project file (`package.json`,
     `Cargo.toml`, ...) with the lint and test tools, and one smoke test of the language.
   - `steering/project/PRINCIPLES.md`: the answers of step 4. One principle per philosophy answer (`## P1. <rule>`,
     2 or 3 lines: what wins, and one example of this project). The section "Owner involvement": the areas of
     "Your decisions". The section "Try a feature": the way of "Try a feature", with what the agents make for it.
   - `CLAUDE.md`: the rule of P1 in one line in a section "Rules of the domain" (each run reads `CLAUDE.md`).
   - `[owner_tasks]` in `agent.toml`: with a test ticket, `play` = the words that each test ticket body has
     (for example "Try it on your computer").
   - `.claude/skills/verify/SKILL.md`: with images in each PR, a last level that makes them.
   - `docs/ENVIRONMENT.md`, section "Resources of the owner": the answers of the resource questions of step 3.
   - With a development server: `dev` in `[commands]` (for example `python3 -m http.server`, `npm run dev`), and a
     feature in the first goal of the roadmap that makes it work. Else delete `.claude/skills/try/`.
   - `.claude/skills/roadmap/SKILL.md`: keep it. The runs make the epics with it.
3. Remove what the project does not need:
   - `weights` in `[pacing]` of `steering/system/system.toml`, from the "Runs" answer: `{}` (one main task),
     `{ haiku = 0.25 }`, or `{ haiku = 0.25, deep = 4.0 }` with `reserved = ["haiku", "deep"]`. Each lane is a
     scheduled task and two secrets more for the owner.
   - `.claude/skills/new-project/`: delete it, unless the owner wants to make more projects from the new one.
   - `.claude/settings.json`: add `allow` rules for the commands of the stack (for example `Bash(npm:*)`,
     `Bash(cargo:*)`). Remove nothing from `deny`.
   - The list "Write these specific files" that the bootstrap printed names the specific files of the source project.
     Most belong only to it (its design, demo and human skills, its release and site workflows): leave them out. Write
     only the ones that this project needs (for example `steering/project/DECISIONS.md`, empty), and name the others
     in the report in one line.
4. In DIR, run the install, lint and fast test commands. All must pass before step 7. Fix the files, not the tests.

## 7. Make the repository

**With `gh` (a local session):**

1. `python3 framework/tools/new_repo.py DIR --repo OWNER/NAME --description "<one line>" --dry-run`, then the same
   without `--dry-run` (`--private` when the owner selected it). The tool makes the first commit, the repository,
   the push, the workflow permissions, the ruleset `Protect main`, the labels and the status issue.
2. Read each `FAIL` line. Fix the cause and run the tool again: it skips the steps that are done.

**With no `gh` (a cloud session):** the session can push only to this repository.

1. Commit DIR as a new branch with no history: `git -C DIR init -b new-project/NAME`, `git -C DIR add -A`, commit,
   then push it to this repository (`git -C DIR push <the URL of origin of this clone> new-project/NAME`).
2. Give the owner these commands for a terminal on a computer with `gh auth login` done:

       git clone -b new-project/NAME --single-branch <the URL of this repository> NAME && cd NAME
       git branch -m main && git remote remove origin
       python3 framework/tools/new_repo.py . --repo OWNER/NAME --description "<one line>"

3. When the owner says that it is done, delete the branch `new-project/NAME` of this repository. Then continue with
   step 8. Give the commands of step 8 with `.` in place of DIR, for the clone of the owner.

## 8. Guide the owner

Guide the owner through the steps that need the owner's accounts, **one step at a time** (with a browser tool, do the
clicks yourself: below). For each step: give the exact
clicks and the values to paste (the real repository name, the real task names), then ask with AskUserQuestion
"Done", "Problem" (the owner says what went wrong; help, then ask again) or "Later" (put the step in the report).
After each step that GitHub can show, run `python3 framework/tools/new_repo.py DIR --repo OWNER/NAME --check` and say
the result in one line. When the session has the tool `read_documentation`, read the page of the step first and use
its current clicks: the app changes faster than this text.

1. **Claude GitHub app.** Open https://github.com/apps/claude/installations/select_target, select the account, and
   add the repository OWNER/NAME to the installation.
2. **Cloud environment.** At claude.ai/code, make a new environment "NAME": "Allow package managers" on, the whole
   file `scripts/allowed-domains.txt` in "Allowed domains", the whole file `scripts/cloud-setup.sh` as the setup
   script. Show both files in the chat in code blocks, ready to copy.
3. **Scheduled task "NAME autopilot".** At claude.ai/code/routines (the app calls the scheduled tasks "Routines"), click
   "New task" → "Set up manually", and set: the name "NAME autopilot", the repository OWNER/NAME, the environment of
   item 2, no schedule (the pacer starts it), the prompt `/scheduled max`, and the model Opus with "Effort" (a submenu
   of the model menu) at low. Then add the trigger type "API" in the task form and click "Create". The token shows once,
   after "Create": the owner copies it for item 5. Open the task page and click "Copy fire URL". The task ID is the end
   of the page address (`trig_...`). Keep the fire URL and the task ID for items 5 and 6.
4. **The lane tasks** (only for each lane of `weights`): the same as item 3, with the name "NAME autopilot <lane>",
   the prompt `/scheduled max lane <lane>`, and "a new session on each fire". haiku: Haiku. deep: Opus, Effort high.
5. **Secrets.** Open the Terminal panel of the desktop app and type one line there:
   `claude setup-token && python3 framework/tools/new_repo.py DIR --repo OWNER/NAME --secrets`. `claude setup-token`
   prints the token in that tab; the owner copies it from there. If it signs in with the wrong account, the owner
   switches the account in the default browser first, then runs the line again. The `--secrets` prompt, with no echo,
   asks in this order: `CLAUDE_CODE_OAUTH_TOKEN`, then the fire URL and the token of main, then the fire URL and the
   token of each lane in the order of `secret_names()`. Tell the owner this order. The agent never reads the Terminal
   tab and never reads a secret. In a cloud session, give the same line for the owner's terminal, or the names of
   `--dry-run --secrets` for GitHub → Settings → Secrets and variables → Actions → "New repository secret". Never ask
   for a secret value in the chat.
6. **The task ID.** Ask the owner for the ID of "NAME autopilot" (it is no secret). Write it to `trigger` in
   `[pacing]` of `DIR/steering/system/system.toml`, commit, push to the default branch, and run
   `python3 framework/tools/new_repo.py DIR --repo OWNER/NAME --start`. In a cloud session, give the owner the two
   lines to change and the commands.

**With a browser tool** (Claude in Chrome or the built-in browser of the desktop app; load its skill first): ask the
owner once with AskUserQuestion: "I do the clicks (Recommended)" or "You do the clicks". When you do them, open each
page in a new tab with the owner's sign-in, fill the forms, and show the result. These limits stay:
- Stop before each grant of access (the "Install" of the GitHub app, a sign-in, a new connection): the owner clicks it.
- Never read, copy or type a secret value (the token of an API trigger, of `claude setup-token`). When a page shows
  one, tell the owner to copy it, then use the `--secrets` prompt of item 5. A fire URL and a task ID are no secrets.
- Item 5 needs a terminal: the owner runs its line in the Terminal panel.
- When a page differs from the steps, or asks for a payment, stop and ask the owner.

At the end, run `--check` again. Each `MISSING` line goes into the report with its step.

## 9. Check and report

1. `python3 framework/tools/new_repo.py DIR --repo OWNER/NAME --check` and `gh run list --repo OWNER/NAME --limit 5`:
   CI and Pacer start.
2. Tell the owner: the repository URL, the roadmap goals, the stack, the principles, the steps put "Later", how to
   try a feature (with a development server: `/try` in a local session of a clone), and what the first run does (it makes the
   epics and the tickets from the roadmap). The owner steers through issues from then on
   (`framework/docs/STEERING.md`). To change the direction later, the owner edits `steering/project/PRINCIPLES.md`.
