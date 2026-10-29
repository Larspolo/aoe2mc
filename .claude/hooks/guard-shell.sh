#!/bin/bash
# PreToolUse hook: block the shell commands that cost runs time (docs/LEARNINGS.md). Exit 2 blocks the command and
# shows the message to the agent. Each rule names its way around.
exec python3 -c '
import json, os, re, shlex, subprocess, sys
data = json.load(sys.stdin)
raw = (data.get("tool_input") or {}).get("command") or ""
cwd = data.get("cwd") or "."
def git(*args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True).stdout.strip()
def words(seg):
    try:
        return shlex.split(seg)
    except ValueError:
        return seg.split()
def why():
    cmd = re.sub(r"(<<-?\s*([\x27\x22]?)(\w+)\2[^\n]*)\n.*?\n\s*\3\b", r"\1", raw, flags=re.S)  # heredoc bodies are text
    for m in re.finditer(r"\bcat\s*>\s*([^\s|;&<>()]+)\s*<<", cmd):           # ">|" is the way around
        f = m.group(1).strip("\x27\x22")
        if "$" not in f and git("ls-files", "--", f):
            return (f"cat > {f} writes over a file that git tracks (#1945). Use the Edit tool, or write >| {f} "
                    "if you really mean to replace it.")
    assigned = set(re.findall(r"(?:^|[\s;&|(])(?:export\s+)?(\w+)=", cmd)) | set(re.findall(r"\bfor\s+(\w+)\s+in\b", cmd))
    for m in re.finditer(r"(?<![<>&\d])>>?\s*\x22?\$\{?(\w+)\}?/", cmd):
        v = m.group(1)
        if v != "TMPDIR" and not os.environ.get(v) and v not in assigned:
            return (f"${v} is empty here, so the redirect writes to /... (#2032, #865). Write the full path, "
                    "or set the variable on its own line (not in an & list).")
    for seg in re.split(r"&&|\|\||[;\n]", cmd):
        w = words(seg)
        for tool in ("pkill", "pgrep"):
            if tool in w and (tool == "pkill" or "kill" in w[w.index(tool):]):
                rest = w[w.index(tool) + 1:]
                if any(a.startswith("-") and "f" in a.lstrip("-") and not a.startswith("--") for a in rest):
                    pat = next((a for a in rest if not a.startswith("-")), "")
                    if "[" not in pat:
                        return (f"{tool} -f \"{pat}\" also matches the shell that runs this command, and kills it "
                                f"(#1213). Write a bracket in the pattern, for example \"[{pat[:1]}]{pat[1:]}\".")
        if re.match(r"\s*\(?\s*git\s+(?:-C\s+\S+\s+)?stash\b", seg):
            sub = (w[w.index("stash") + 1:] or ["push"])[0]
            merge = git("rev-parse", "--git-path", "MERGE_HEAD")
            if sub not in ("list", "show") and merge and os.path.exists(os.path.join(cwd, merge)):
                return ("git stash in an unfinished merge drops MERGE_HEAD: the next commit is no merge commit "
                        "(#2281). Finish or abort the merge first, or test main in a git worktree.")
    return None
msg = why()
if msg:
    print("Blocked by .claude/hooks/guard-shell.sh: " + msg, file=sys.stderr)
    sys.exit(2)
'
