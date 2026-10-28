"""A `#` line inside a folded `if: >-` is part of the expression: GitHub then refuses the whole workflow (#3468)."""
import glob
import os
import re

WORKFLOWS = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "*.yml")


def block_ifs(text):
    """(line number, lines) of each `if:` with a block scalar (`>-`, `>`, `|`): its lines are the expression."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)(?:- )?if:\s*[>|][-+]?\s*$", line)
        if not m:
            continue
        body = []
        for nxt in lines[i + 1:]:
            if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= len(m.group(1)):
                break
            body.append(nxt)
        yield i + 1, body


def comments(text):
    return [(n, s.strip()) for n, body in block_ifs(text) for s in body if s.strip().startswith("#")]


def test_no_comment_in_a_folded_if():
    bad = {os.path.basename(f): c for f in sorted(glob.glob(WORKFLOWS)) if (c := comments(open(f).read()))}
    assert not bad, f"move the comment above `if:` (GitHub: Unexpected symbol: '#'): {bad}"


def test_finds_the_comment_of_3436():
    text = "jobs:\n  merge:\n    if: >-\n      a == 'b' ||\n      c\n      # why\n    runs-on: x\n"
    assert comments(text) == [(3, "# why")]
    assert comments(text.replace("      # why\n", "")) == []
