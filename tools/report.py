"""The run report of autopilot step 8 with one command (#1701): the text, the release bar (`release.py`), the `Usage:`
line of the run start, one `Metrics:` line per ticket and the `Tokens:` line (`tokens.py`). `tools/health.py` parses it.

    python3 tools/report.py --usage "$(cat USAGE)" --text "What I did. Next: ..." \\
        --ticket 1701 --size S --result "pr #1770" --setup 2 --checks 1 --checks-min 4 --sinks none \\
        --phases read=8,claim=1,code=18,verify=9,ci=0,conflict=5,report=4 [--ticket ...] [--post]

Repeat the ticket options for each ticket of the run, in the same order. `--minutes` defaults to the sum of the
phases. `--post` comments the report on the status issue (label `agent-status`), else it prints it.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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


def tool(*args):
    """The output of another tool of this directory, without its trailing newline."""
    r = subprocess.run([sys.executable, os.path.join(HERE, args[0]), *args[1:]], capture_output=True, text=True)
    return r.stdout.rstrip("\n")


def report(text, usage, lines, release=None, tokens=None):
    """The comment: text, release bar, `Usage:`, `Metrics:` and `Tokens:` lines, footer."""
    release = tool("release.py") if release is None else release
    tokens = (tool("tokens.py").splitlines() or [""])[-1] if tokens is None else tokens
    return "\n".join([text.strip(), "", release, "", usage.strip(), *lines, tokens]) + FOOTER


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

    lines = [metrics(t, a.size[i], a.result[i], at(a.minutes, i, None), at(a.setup, i, 0), at(a.checks, i, 0),
                     at(a.checks_min, i, 0), at(a.sinks, i, "none"), at(a.phases, i, ""), at(a.lane, i, None))
             for i, t in enumerate(a.ticket)]
    usage = a.usage or (tool("usage.py", "--sample").splitlines() or [""])[-1]
    body = report(a.text, usage, lines)
    if not a.post:
        print(body)
        return 0
    status = next(i for i in pages(f"issues?state=open&labels={STATUS}") if "pull_request" not in i)
    print(api(f"issues/{status['number']}/comments", "POST", {"body": body})["html_url"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
