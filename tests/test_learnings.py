"""docs/LEARNINGS.md loads into each turn of each run: keep it at 80 lines or less (#1698)."""
from pathlib import Path


def test_learnings_has_80_lines_or_less():
    n = len((Path(__file__).parent.parent / "docs" / "LEARNINGS.md").read_text().splitlines())
    assert n <= 80, f"docs/LEARNINGS.md has {n} lines: merge lines, or move topic pitfalls to their documents"
