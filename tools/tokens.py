"""The tokens of this run and their sinks: one data source to find the bottleneck of the system (owner, 2026-10-27).

Claude Code writes each session to `~/.claude/projects/<cwd with - for />/<session>.jsonl` (subagents in
`<session>/subagents/*.jsonl`). Each API call has a `usage` record. This tool adds them and finds the tool results
that cost the most: a result stays in the context, so each later call reads it again from the cache.

    python3 tools/tokens.py               # the Tokens: line of the newest session (autopilot step 8)
    python3 tools/tokens.py --top 15      # the 15 largest sinks, one per line
    python3 tools/tokens.py FILE.jsonl    # another transcript
    python3 tools/tokens.py --verify      # the minutes and repeats of each check command (#1704)

The unit is "eq": input-token equivalents with the API price ratios (input 1, cache write 1.25 for 5 minutes and 2 for
1 hour, cache read 0.1, output 5). The subscription quota is not public, but it follows the cost of the calls.
A sink costs its tokens (about 4 characters each) written once to the cache, then read by each later call of its chain.
Sink `base`: the system prompt, the tools, CLAUDE.md and LEARNINGS, which each call reads again; `repo` is the part
in the repository (CLAUDE.md and its `@` files), the rest only the environment settings change (connectors, tools). Sink `output`: text,
thinking and tool input. The rest of the eq (not in the sinks): owner messages, hook text and the carried output.
Field `cost`: the API list price of the calls in $, by the model of each call (`PRICES`). The eq weighs a cache read
0.1, but Opus 5.5 pays 0.05 and Haiku 5.5 pays 5 times more above 100k prompt tokens: compare lanes by the cost.
Field `verify` (#1704): the wall minutes and the count of the check commands (`pytest`, `ruff`, `mc_check.py`, `mc_shot.py`,
`render.py`, and `wait`: a loop that waits for the output of a background check), from the time of a tool call to the
time of its result. A background command has its minutes in the wait loop or the notification, not in its own call.
The pure functions take plain records, so the tests need no files.
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

W_IN, W_5M, W_1H, W_READ, W_OUT = 1.0, 1.25, 2.0, 0.1, 5.0
CHARS = 4                    # characters per token (an estimate: the transcript has no token count of a result)
IMAGE = 1600                 # tokens of an image in a tool result (an estimate)
# API list prices in $ per million tokens (input, output, cache read; a cache write is the input price × W_5M or W_1H),
# 2026-10. A second row is the price of a prompt above LONG tokens.
PRICES = {
    "claude-fable-5-1": ((10.0, 50.0, 0.25),),
    "claude-haiku-5-5": ((0.10, 0.50, 0.01), (0.50, 2.50, 0.05)),
    "claude-opus-5": ((5.0, 25.0, 0.50),),
    "claude-opus-5-5": ((4.0, 20.0, 0.20),),
    "claude-sonnet-5-5": ((2.0, 10.0, 0.20),),
}
LONG = 100_000


def eq(u):
    """Input-token equivalents of one `usage` record."""
    cc = u.get("cache_creation") or {}
    h1 = cc.get("ephemeral_1h_input_tokens", 0)
    m5 = cc.get("ephemeral_5m_input_tokens", (u.get("cache_creation_input_tokens") or 0) - h1)
    return (W_IN * (u.get("input_tokens") or 0) + W_5M * m5 + W_1H * h1 + W_READ * (u.get("cache_read_input_tokens") or 0)
            + W_OUT * (u.get("output_tokens") or 0))


def usd(u, model):
    """The API list price in $ of one `usage` record of `model`, or None for a model without a price."""
    rows = PRICES.get((model or "").split("[")[0])
    if not rows:
        return None
    cc = u.get("cache_creation") or {}
    write = u.get("cache_creation_input_tokens") or 0
    h1 = cc.get("ephemeral_1h_input_tokens", 0)
    m5 = cc.get("ephemeral_5m_input_tokens", write - h1)
    read, fresh = u.get("cache_read_input_tokens") or 0, u.get("input_tokens") or 0
    p_in, p_out, p_read = rows[-1] if fresh + write + read > LONG else rows[0]
    return (p_in * (fresh + W_5M * m5 + W_1H * h1) + p_read * read + p_out * (u.get("output_tokens") or 0)) / 1e6


def label(name, inp):
    """A short sink key that groups calls of the same kind over runs: `Bash pytest`, `Read tools/x.py`, `Skill design`."""
    if name == "Bash":
        cmd = inp.get("command", "")
        cmd = re.sub(r"^(\s*(cd \S+|[A-Z_]+=\S+|export \S+)\s*(&&|;)?\s*)+", "", cmd).strip()
        words = [w for w in re.split(r"[\s|;&]+", cmd) if w and not w.startswith(("-", "'", '"'))
                 and not re.fullmatch(r"[\d,$p]+", w)][:4]
        if words[:1] == ["python3"] and len(words) > 1:
            words = words[1:]
        if words[:1] == ["timeout"]:
            words = words[2:]
        return "Bash " + " ".join(w.rsplit("/", 1)[-1] if "/" in w and w.endswith(".py") else w for w in words[:2])
    if name in ("Read", "Edit", "Write"):
        p = inp.get("file_path", "")
        return f"{name} " + re.sub(r"^/home/user/[^/]+/", "", p)
    if name in ("Grep", "Glob"):
        return name
    if name == "Skill":
        return "Skill " + inp.get("skill", "")
    if name == "Agent":
        return "Agent " + inp.get("subagent_type", "general")
    if name.startswith("mcp__"):
        return "mcp " + name.split("__")[-1]
    return name


CHECKS = (("pytest -m mc", r"pytest\b.*-m\s+['\"]?mc\b"), ("pytest -m slow", r"pytest\b.*-m\s+['\"]?slow\b"),
          ("pytest files", r"pytest\b.*\btests/\S+\.py"), ("pytest", r"\bpytest\b"), ("ruff", r"\bruff\b"),
          ("mc_check.py", r"mc_check\.py"), ("mc_shot.py", r"mc_shot\.py"), ("render.py", r"render\.py"))
WAIT = r"\buntil\b|\bsleep\b"                 # a wait loop (LEARNINGS #413): its minutes are the minutes of a check
OUTPUT = r"rc=|\.out\b|\.log\b"               # the output of a background check that a wait loop reads
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?.*?^\s*\1\s*$", re.M | re.S)   # text (a PR body, a file), no command


def check(cmd):
    """The check kind of a Bash command, or None. A command with several checks (`ruff && pytest`) gets the first
    one of CHECKS, the one that takes the most time. A wait loop for the output of a check is `wait`, a wait loop for
    something else (a server) is None. The text of a heredoc does not count."""
    cmd = HEREDOC.sub("", cmd)
    if re.search(WAIT, cmd):
        return "wait" if re.search("|".join(rx for _, rx in CHECKS) + "|" + OUTPUT, cmd) else None
    return next((k for k, rx in CHECKS if re.search(rx, cmd)), None)


def when(r):
    """The time of a transcript record in seconds, or None."""
    t = r.get("timestamp")
    return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp() if t else None


def verify(records):
    """{check kind: [wall minutes, count]} of the check commands of one chain of records (#1704)."""
    start, out = {}, defaultdict(lambda: [0.0, 0])
    for r in records:
        msg = r.get("message") or {}
        content = msg.get("content")
        if r.get("type") == "assistant" and isinstance(content, list):
            for b in content:
                if b.get("type") == "tool_use" and b.get("name") == "Bash":
                    k = check((b.get("input") or {}).get("command", ""))
                    if k:
                        start[b["id"]] = (k, when(r))
        elif r.get("type") == "user" and isinstance(content, list):
            for b in content:
                if b.get("type") == "tool_result" and b.get("tool_use_id") in start:
                    k, t0 = start.pop(b["tool_use_id"])
                    t1 = when(r)
                    out[k][0] += (t1 - t0) / 60 if t0 is not None and t1 is not None else 0
                    out[k][1] += 1
    return dict(out)


def verify_field(v, k=4):
    """The `verify` field of the Tokens: line: the k check kinds with the most minutes (`pytest 4.1m 2x`)."""
    top = sorted(v.items(), key=lambda kv: -kv[1][0])[:k]
    return "verify " + (", ".join(f"{s} {m:.1f}m {n}x" for s, (m, n) in top) or "-")


def size(content):
    """Tokens of a tool result (string or list of blocks)."""
    if isinstance(content, str):
        return len(content) / CHARS
    return sum(len(b.get("text", "")) / CHARS if b.get("type") == "text" else IMAGE if b.get("type") == "image" else 0
               for b in content or [])


def analyse(records):
    """Totals and sinks of one chain of transcript records (in file order).
    Returns {"eq", "calls", "in", "write", "read", "out", "peak", "base", "sinks": {label: eq}}."""
    seen, calls, uses = set(), [], {}
    t = dict.fromkeys(("eq", "in", "write", "read", "out", "peak", "base", "usd", "unpriced"), 0.0)
    results = []                                    # (label, tokens, index of the next call)
    for r in records:
        msg = r.get("message") or {}
        if r.get("type") == "assistant":
            for b in msg.get("content") or []:
                if b.get("type") == "tool_use":
                    uses[b["id"]] = label(b.get("name", ""), b.get("input") or {})
            u = msg.get("usage")
            if u and msg.get("id") not in seen:     # one record per content block, all with the same usage
                seen.add(msg.get("id"))
                calls.append(u)
                t["eq"] += eq(u)
                d = usd(u, msg.get("model"))
                t["usd"] += d or 0
                t["unpriced"] += d is None
                t["in"] += u.get("input_tokens") or 0
                t["write"] += u.get("cache_creation_input_tokens") or 0
                t["read"] += u.get("cache_read_input_tokens") or 0
                t["out"] += u.get("output_tokens") or 0
                ctx = sum(u.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
                t["peak"] = max(t["peak"], ctx)
                if len(calls) == 1:
                    t["base"] = ctx                 # the system prompt, tools, CLAUDE.md and LEARNINGS of each call
        elif r.get("type") == "user" and isinstance(msg.get("content"), list):
            for b in msg["content"]:
                if b.get("type") == "tool_result":
                    results.append((uses.get(b.get("tool_use_id"), "?"), size(b.get("content")), len(calls)))
    n = len(calls)
    sinks = defaultdict(float)
    for lab, tok, at in results:
        sinks[lab] += tok * (W_1H + W_READ * max(n - at - 1, 0))
    first = calls[0] if calls else {}
    sinks["base"] = eq(first) - W_OUT * (first.get("output_tokens") or 0) \
        + t["base"] * W_READ * max(n - 1, 0)
    sinks["output"] = W_OUT * t["out"]
    t["calls"], t["sinks"] = n, dict(sinks)
    return t


def merge(parts):
    out = {"sinks": defaultdict(float)}
    for p in parts:
        for k, v in p.items():
            if k == "sinks":
                for s, x in v.items():
                    out["sinks"][s] += x
            elif k == "peak":
                out[k] = max(out.get(k, 0), v)
            elif k == "base":
                out.setdefault(k, v)                # the base of the main chain (the first part)
            else:
                out[k] = out.get(k, 0) + v
    return out


def kind(lab):
    """The group of a sink for the Tokens: line: the tool, and the program of a command (`Read`, `Bash pytest`)."""
    if lab.startswith("Bash"):
        return " ".join(lab.split(" ")[:2])
    return lab if lab.startswith(("base", "output", "Skill", "mcp", "Agent")) else lab.split(" ", 1)[0]


def line(t, k=5, repo=None, checks=None):
    """The `Tokens:` line of the run report (tools/health.py reads it). checks: the verify() of the run (#1704)."""
    g = defaultdict(float)
    for s, x in t["sinks"].items():
        g[kind(s)] += x
    top = sorted(g.items(), key=lambda kv: -kv[1])[:k]
    m = lambda x: f"{x / 1e6:.2f}M"
    return (f"Tokens: {m(t['eq'])} eq · calls {t['calls']} · write {m(t['write'])} · read {m(t['read'])} · "
            f"out {m(t['out'])} · cost ${t.get('usd', 0):.2f}"
            + (f" (+{t['unpriced']:.0f} calls without a price)" if t.get("unpriced") else "")
            + f" · peak {t['peak'] / 1e3:.0f}k · base {t['base'] / 1e3:.0f}k"
            + ("" if repo is None else f" (repo {repo / 1e3:.0f}k)")
            + ("" if checks is None else " · " + verify_field(checks)) + " · sinks "
            + ", ".join(f"{s} {x / t['eq']:.0%}" for s, x in top))


def repo_base(root="."):
    """Tokens of the base that the repository controls: CLAUDE.md and the files that it loads with `@path` lines."""
    try:
        text = open(os.path.join(root, "CLAUDE.md")).read()
    except OSError:
        return 0
    n = len(text)
    for inc in re.findall(r"^@(\S+)$", text, re.M):
        try:
            n += len(open(os.path.join(root, inc)).read())
        except OSError:
            pass
    return n / CHARS


def load(path):
    with open(path) as f:
        return [json.loads(x) for x in f if x.strip()]


def newest(cwd=None):
    d = os.path.expanduser("~/.claude/projects/" + re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(cwd or os.getcwd())))
    fs = sorted(glob.glob(os.path.join(d, "*.jsonl")), key=os.path.getmtime)
    return fs[-1] if fs else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("file", nargs="?", help="a transcript (default: the newest session of this directory)")
    ap.add_argument("--top", type=int, help="print the N largest sinks, one per line")
    ap.add_argument("--verify", action="store_true", help="print each check command kind: minutes and count (#1704)")
    a = ap.parse_args(argv)
    path = a.file or newest()
    if not path:
        sys.exit("no transcript in ~/.claude/projects for this directory")
    subs = sorted(glob.glob(os.path.join(path[:-len(".jsonl")], "subagents", "*.jsonl")))
    chains = [load(path)] + [load(s) for s in subs]
    t = merge([analyse(c) for c in chains])
    v = defaultdict(lambda: [0.0, 0])
    for c in chains:
        for s, (m, n) in verify(c).items():
            v[s][0] += m
            v[s][1] += n
    print(line(t, repo=repo_base(), checks=dict(v)))
    if a.verify:
        for s, (m, n) in sorted(v.items(), key=lambda kv: -kv[1][0]):
            print(f"  {m:6.1f} min  {n:3d}x  {s}")
    for s, x in sorted(t["sinks"].items(), key=lambda kv: -kv[1])[:a.top or 0]:
        print(f"  {x / t['eq']:5.1%}  {x / 1e3:8.0f}k  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
