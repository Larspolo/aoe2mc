#!/bin/bash
# PreToolUse hook of the MCP tools that write an issue, a comment or a PR: block a body that is only a file path
# (#4250: GitHub stores "@/path/t.md" as the text). Exit 2 blocks the call and shows the message to the agent.
exec python3 -c '
import json, re, sys
body = (json.load(sys.stdin).get("tool_input") or {}).get("body") or ""
first = next((line for line in body.splitlines() if line.strip()), "")
if re.fullmatch(r"\s*@\S+\s*", first):
    print("Blocked by .claude/hooks/guard-body.sh: the body is only a file path. Read the file and pass its text.",
          file=sys.stderr)
    sys.exit(2)
'
