"""The rows of the real steering/project/RELEASE.md: each row has the cells of its header, and release.release() reads the
ticket of each check row (#3053: six check rows had their ticket in a sixth cell, and all read "ticket None")."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import release  # noqa: E402

TEXT = open(os.path.join(ROOT, "steering", "project", "RELEASE.md"), encoding="utf-8").read()


def cells(line):
    return line.strip().strip("|").split("|")


def tables():
    """[(header cells, [rows])] of the tables of the file."""
    out = []
    for line in TEXT.splitlines():
        if not line.startswith("|"):
            out.append(None)
        elif out and out[-1]:
            out[-1][1].append(line)
        else:
            out.append((cells(line), []))
    return [t for t in out if t]


def test_each_row_has_the_cells_of_its_header():
    bad = [line for head, rows in tables() for line in rows if len(cells(line)) != len(head)]
    assert not bad, bad


def test_each_row_with_a_ticket_gives_it_to_release():
    tickets = {key: ticket for _, key, _, _, ticket in release.release(TEXT)[1]}
    want = {m[1]: int(n[1]) for head, rows in tables() if head[-1].strip() == "ticket" for line in rows
            if (m := re.match(r"\| `([^`]+)`", line)) and (n := re.search(r"#(\d+)", cells(line)[-1]))}
    assert want and all(tickets.get(k) == v for k, v in want.items()), (want, tickets)
