"""No '#' comment line in a folded `if:` of a workflow: GitHub reads it as expression text, and the whole workflow
fails to parse (422 on dispatch, #3464)."""
import os
import re

FLOWS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".github", "workflows")


def comments_in_folded_ifs(text):
    """(line number, line) of each '#' line inside an `if: >` or `if: |` block."""
    out, indent = [], None
    for n, line in enumerate(text.splitlines(), 1):
        if indent is not None:
            if line.strip() and len(line) - len(line.lstrip()) <= indent:
                indent = None
            elif line.lstrip().startswith("#"):
                out.append((n, line))
        if indent is None and (m := re.match(r"(\s*)(?:- )?if:\s*[>|][-+]?\s*$", line)):
            indent = len(m.group(1))
    return out


def test_the_check_finds_a_comment():
    text = "jobs:\n  a:\n    if: >-\n      # why\n      true\n    runs-on: x\n    # a normal comment\n"
    assert comments_in_folded_ifs(text) == [(4, "      # why")]


def test_no_comment_in_a_folded_if():
    bad = {f: c for f in sorted(os.listdir(FLOWS)) if (c := comments_in_folded_ifs(open(os.path.join(FLOWS, f)).read()))}
    assert not bad, f"move each comment above the `if:` key: {bad}"
