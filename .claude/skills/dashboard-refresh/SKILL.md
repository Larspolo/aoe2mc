---
name: dashboard-refresh
description: Refresh the data files of the owner's dashboard artifact (aoe2mc Autopilot, the URL is `dashboard.artifact` in agent.toml) from GitHub and the repository. Use when the owner types "/dashboard-refresh", and in the hourly scheduled task "aoe2mc dashboard refresh". Needs a session with the Artifact and ArtifactData tools.
---

# Dashboard refresh

Since 2026-10-28 (owner decision A) the workflow `dashboard-site.yml` builds the same page with `tools/dashboard_site.py`
and publishes it to GitHub Pages each pacer cycle. This skill is the fallback for the claude.ai artifact.

The dashboard artifact has four tabs (Activity, Progress, Tickets, Setup). Its page reads data files that are
attached to the artifact: one dataset document for each file in the collection `datasets`. The account has no GitHub
connector, so this skill writes a saved copy (#982). It is not the #1 dashboard (`tools/dashboard.py`).

| Dataset | File | Source |
|---|---|---|
| `merges` | `aoe2mc-merged-prs.json` | GitHub pulls (state closed) |
| `tickets` | `aoe2mc-tickets.json` | GitHub issues (state all), also the `priority` column for the bands of "Open tickets over time", `parent` (the epic of a sub-issue) for "Progress over time" and `haiku` (label `lane:haiku`) |
| `epics` | `aoe2mc-epics.json` | GitHub issues with label `epic`, the "Roadmap: `key`" line |
| `roadmap` | `aoe2mc-roadmap.json` | `docs/ROADMAP.md` |
| `release_bar` | `aoe2mc-release-bar.json` | `docs/RELEASE.md` (the same rules as `tools/release.py`) |
| `usage` | `aoe2mc-usage.json` | the `Usage:` lines on the status issue (7 days): 5-hour `usage` and `resets`, `runs` and the Haiku lane runs `haiku`, 7-day `week`, `week_resets` and the on-track text `track` (#1696) |
| `setup` | `aoe2mc-setup.json` | `tools/dashboard_artifact/setup.json` (written by hand: change it when a part of the setup changes) |

URL = `artifact` of the section `[dashboard]` in `agent.toml`. Do these steps in sequence:

1. Pull `main`. Run `python3 tools/dashboard_data.py out/dashboard`. It writes the seven files, prints the rows of
   each, and checks the columns (#1031): it compares the columns of each new file with the columns that
   `tools/dashboard_artifact/index.html` reads, and prints `columns: OK` or each file with its missing columns
   (exit 1). The check needs no old asset. A failure (GitHub access or missing columns): stop, change nothing on the
   artifact. Missing columns: make a `bug` ticket with the printed lines.
2. Read the dataset documents: `ArtifactData list`, collection `datasets`. Note `version` and `source.url` of each
   (the old asset `/_blob/<id>`).
3. Upload each file: `Artifact` publish with `url` = URL, `asset: true`, `file_path` = `out/dashboard/<file>`.
   One file per call (a JSON file cannot share a call). Note the new `url` of each.
4. Update each dataset document: `ArtifactData update`, collection `datasets`, doc = the dataset,
   `data` = `{"source": {"kind": "file", "name": "<file>", "url": "<new url>"}, "updated": {"at": "<now, ISO>", "by": "Claude"}}`,
   `if_version` = the version of step 2. A version conflict: read the document again and redo only that write.
   Use one `batch` for the seven writes when the tool offers it.
5. Page: read `files/index.html` (`ArtifactData get`, field `text`, with `out_dir`). When
   `tools/dashboard_artifact/index.html` on `main` differs, write it: `ArtifactData set` of `files/index.html` with
   `{"text": <the file>}` and `if_version`. When the artifact page is newer than the copy (the owner changed it),
   do not write it: make a ticket to copy the page into the repository.
6. Read the run documents of the page: `ArtifactData get`, collection `data/users/me`, doc `check`, then doc `runs`.
   The page writes them only when Claude writes the page (step 5), not when a person opens it (#1031). "No document"
   is therefore the usual result of a refresh that wrote only data files: it is no failure, do not wait for it. The
   column check of step 1 is the check of the data. A document that holds a failure (a failed check, a run with an
   error): make a `bug` ticket with its text (look for an open one first). Report the result in one line, for example
   "check: none (no page write), runs: none, columns: OK".
7. Delete the old files: `Artifact` delete with `url` = URL and `path` = each old asset id of step 2 (only ids that no
   dataset uses now). The auto mode of an unattended run can deny this delete (2026-10-26, #982): do not try another
   way; list the old ids in the report. The page uses only the ids of the dataset documents. Do not read the old
   assets: a cloud session cannot read an uploaded asset ("not found through this cloud session's artifact mount").

## The hourly scheduled task

The owner (or the `operator` skill) makes it. Runs of the autopilot have no trigger tools (#566).
Name: "aoe2mc dashboard refresh". Schedule: hourly at :50. Repository: the project repository, a fresh session.
Prompt: "Pull main of the repository. Follow .claude/skills/dashboard-refresh/SKILL.md. Do not change files in the
repository and do not open a pull request."
