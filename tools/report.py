"""The run report of autopilot step 8 with one command (#1701): the text, the release bar (`release.py`), the `Usage:`
line of the run start (the release bar only when the project has `release.py`), one `Metrics:` line per ticket, the `Tokens:`, `Calls:` and `Run:` lines (`tokens.py`). `tools/health.py` parses it.

    python3 tools/report.py --usage "$(cat USAGE)" --text "What I did. Next: ..." \\
        --ticket 1701 --size S --result "pr #1770" --setup 2 --checks 1 --checks-min 4 --sinks none \\
        --phases read=8,claim=1,code=18,verify=9,ci=0,conflict=5,report=4 [--ticket ...] [--post]

Repeat the ticket options for each ticket of the run, in the same order. `--minutes` defaults to the sum of the
phases. Without `--phases` a ticket gets the phases that `tokens.py --phases` measures in the transcript. `--post` comments the report on the status issue (label `agent-status`) and sets `last_run` and `runs` of its
state comment, else it prints the comment.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from claim import agent_state, utc, with_state  # noqa: E402
from dashboard import FOOTER, STATUS, api, pages  # noqa: E402
from health import PHASES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def phases(text):
    """{phase: minutes} of `read=8,code=18,...`; a phase that is not named is 0."""
    out = dict.fromkeys(PHASES, 0.0)
    for part in filter(None, text.split(",")):
        k, _, v = part.partition("=")
        if k.strip() not in out:
            raise ValueError(f"unknown phase {k!r}: use {', '.join(PHASES)}")
        out[k.strip()] = float(v)
    return out


def num(x):
    return f"{x:g}"


def metrics(ticket, size, result, minutes=None, setup=0, checks=0, checks_min=0, sinks="none", phase="", lane=None):
    """One `Metrics:` line in the format of autopilot step 8."""
    p = phases(phase)
    minutes = sum(p.values()) if minutes is None else minutes
    size = size if size.startswith("size:") else f"size:{size}"
    return (f"Metrics: ticket #{ticket} · {size} · {result} · {num(minutes)} min · setup {num(setup)} min · "
            f"checks {checks} · checks {num(checks_min)} min · time sinks: {sinks or 'none'} · phases "
            + " · ".join(f"{k} {num(v)}" for k, v in p.items()) + (f" · lane {lane}" if lane else ""))


def git_lane():
    """The lane of the run: `git config aoe2mc.lane` (the Haiku lane sets it, #1727), else None (#1982)."""
    r = subprocess.run(["git", "config", "--get", "aoe2mc.lane"], capture_output=True, text=True)
    return r.stdout.strip() or None


def tool(*args):
    """The output of another tool of this directory, without its trailing newline; "" when the project has no such
    tool or it fails (a new project has no `release.py`, #1963)."""
    path = os.path.join(HERE, args[0])
    if not os.path.exists(path):
        return ""
    r = subprocess.run([sys.executable, path, *args[1:]], capture_output=True, text=True)
    return r.stdout.rstrip("\n") if r.returncode == 0 else ""


def measured():
    """{ticket: "read=8,claim=1,..."} of this session (`tokens.py --phases`): the phases of a ticket without `--phases`.
    The key "None" holds the time of a run with no won claim."""
    return {m[1]: m[2] for m in re.finditer(r"^#(\d+|None): (\S+)$", tool("tokens.py", "--phases"), re.M)}


def report(text, usage, lines, release=None, tokens=None, calls=None, run=None, lane=None):
    """The comment: text, release bar (none when it is empty), `Usage:`, `Metrics:`, `Tokens:`, `Calls:` and `Run:`
    lines, footer. The `Run:` line ends with the lane of the run (`opus` when the run set none, as in `health.lanes`)."""
    release = tool("release.py") if release is None else release
    tokens = (tool("tokens.py").splitlines() or [""])[-1] if tokens is None else tokens
    calls = tool("tokens.py", "--calls-line") if calls is None else calls
    run = tool("tokens.py", "--run-line") if run is None else run
    lane = git_lane() if lane is None else lane
    return "\n".join([text.strip(), "", *([release, ""] if release else []), usage.strip(), *lines, tokens,
                      *([calls] if calls else []), *([f"{run} · lane {lane or 'opus'}"] if run else [])]) + FOOTER


def counted(body, now=None):
    """The body of the status issue after one more run: `last_run` now, `runs` + 1, the other state keys stay."""
    state = agent_state(body)
    return with_state(body, {**state, "last_run": utc(now), "runs": state.get("runs", 0) + 1})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--text", required=True, help="what the run did and what is next")
    ap.add_argument("--usage", help="the Usage: line of the run start (usage.py --sample); default: a new sample")
    for name, kind in (("ticket", int), ("size", str), ("result", str), ("minutes", float), ("setup", float),
                       ("checks", int), ("checks-min", float), ("sinks", str), ("phases", str), ("lane", str)):
        ap.add_argument(f"--{name}", type=kind, action="append", default=[])
    ap.add_argument("--post", action="store_true", help="comment the report on the status issue")
    a = ap.parse_args(argv)
    n = len(a.ticket)
    for name in ("size", "result"):
        if len(getattr(a, name)) != n:
            ap.error(f"give --{name} once for each --ticket")

    def at(values, i, default):
        return values[i] if i < len(values) else default

    lane = git_lane()
    got = measured() if len(a.phases) < n else {}
    own = lambda t: got.get(str(t)) or (got.get("None", "") if n == 1 else "")    # measured, not guessed (2026-10-28)
    lines = [metrics(t, a.size[i], a.result[i], at(a.minutes, i, None), at(a.setup, i, 0), at(a.checks, i, 0),
                     at(a.checks_min, i, 0), at(a.sinks, i, "none"), at(a.phases, i, own(t)), at(a.lane, i, lane))
             for i, t in enumerate(a.ticket)]
    usage = a.usage or (tool("usage.py", "--sample").splitlines() or [""])[-1]
    body = report(a.text, usage, lines)
    if not a.post:
        print(body)
        return 0
    status = next(i for i in pages(f"issues?state=open&labels={STATUS}") if "pull_request" not in i)
    print(api(f"issues/{status['number']}/comments", "POST", {"body": body})["html_url"])
    fresh = api(f"issues/{status['number']}")["body"]          # other runs change the body too: read it just before
    api(f"issues/{status['number']}", "PATCH", {"body": counted(fresh)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
