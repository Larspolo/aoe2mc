"""The background check of guard-shell.sh skips an & inside quotes (#5226): only a real & starts a background list."""
import json
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, ".claude", "hooks", "guard-shell.sh")


def run(command):
    return subprocess.run([HOOK], input=json.dumps({"tool_input": {"command": command}, "cwd": ROOT}),
                          capture_output=True, text=True).returncode


@pytest.mark.parametrize("command", [
    'x=$(gh api "a?b=1&page=2"); echo $x',
    "x=$(gh api 'a?b=1&page=2'); echo $x",
    'keys=$( (gh api "repos/o/n/issues?labels=epic&per_page=100&page=2" | jq length) ); echo $keys',
])
def test_quoted_ampersand_passes(command):
    assert run(command) == 0


@pytest.mark.parametrize("command", ["x=1 & echo $x", 'x="a b" & echo "$x"'])
def test_real_background_list_blocks(command):
    assert run(command) == 2
