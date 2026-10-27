"""The tokens of this run and their sinks: one data source to find the bottleneck of the system (owner, 2026-10-27).

Claude Code writes each session to `~/.claude/projects/<cwd with - for />/<session>.jsonl` (subagents in
`<session>/subagents/*.jsonl`). Each API call has a `usage` record. This tool adds them and finds the tool results
that cost the most: a result stays in the context, so each later call reads it again from the cache.

    python3 tools/tokens.py               # the Tokens: line of the newest session (autopilot step 8)
    python3 tools/tokens.py --top 15      # the 15 largest sinks, one per line
    python3 tools/tokens.py FILE.jsonl    # another transcript

The unit is "eq": input-token equivalents with the API price ratios (input 1, cache write 1.25 for 5 minutes and 2 for
1 hour, cache read 0.1, output 5). The subscription quota is not public, but it follows the cost of the calls.
A sink costs its tokens (about 4 characters each) written once to the cache, then read by each later call of its chain.
Sink `base`: the system prompt, the tools, CLAUDE.md and LEARNINGS, which each call reads again; `repo` is the part
in the repository (CLAUDE.md and its `@` files), the rest only the environment settings change (connectors, tools). Sink `output`: text,
thinking and tool input. The rest of the eq (not in the sinks): owner messages, hook text and the carried output.
The pure functions take plain records, so the tests need no files.
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

W_IN, W_5M, W_1H, W_READ, W_OUT = 1.0, 1.25, 2.0, 0.1, 5.0
CHARS = 4                    # characters per token (an estimate: the transcript has no token count of a result)
IMAGE = 1600                 # tokens of an image in a tool result (an estimate)


def eq(u):
    """Input-token equivalents of one `usage` record."""
    cc = u.get("cache_creation") or {}
    h1 = cc.get("ephemeral_1h_input_tokens", 0)
    m5 = cc.get("ephemeral_5m_input_tokens", (u.get("cache_creation_input_tokens") or 0) - h1)
    return (W_IN * (u.get("input_tokens") or 0) + W_5M * m5 + W_1H * h1 + W_READ * (u.get("cache_read_input_tokens") or 0)
            + W_OUT * (u.get("output_tokens") or 0))


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
    t = dict.fromkeys(("eq", "in", "write", "read", "out", "peak", "base"), 0.0)
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


def line(t, k=5, repo=None):
    """The `Tokens:` line of the run report (tools/health.py reads it)."""
    g = defaultdict(float)
    for s, x in t["sinks"].items():
        g[kind(s)] += x
    top = sorted(g.items(), key=lambda kv: -kv[1])[:k]
    m = lambda x: f"{x / 1e6:.2f}M"
    return (f"Tokens: {m(t['eq'])} eq · calls {t['calls']} · write {m(t['write'])} · read {m(t['read'])} · "
            f"out {m(t['out'])} · peak {t['peak'] / 1e3:.0f}k · base {t['base'] / 1e3:.0f}k"
            + ("" if repo is None else f" (repo {repo / 1e3:.0f}k)") + " · sinks "
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
    a = ap.parse_args(argv)
    path = a.file or newest()
    if not path:
        sys.exit("no transcript in ~/.claude/projects for this directory")
    subs = sorted(glob.glob(os.path.join(path[:-len(".jsonl")], "subagents", "*.jsonl")))
    t = merge([analyse(load(path))] + [analyse(load(s)) for s in subs])
    print(line(t, repo=repo_base()))
    for s, x in sorted(t["sinks"].items(), key=lambda kv: -kv[1])[:a.top or 0]:
        print(f"  {x / t['eq']:5.1%}  {x / 1e3:8.0f}k  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
