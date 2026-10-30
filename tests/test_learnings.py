"""docs/LEARNINGS.md loads into each call of each run: keep it at 3000 bytes or less (#1698, #4454)."""
from pathlib import Path


def test_learnings_has_3000_bytes_or_less():
    n = len((Path(__file__).parent.parent / "docs" / "LEARNINGS.md").read_bytes())
    assert n <= 3000, f"docs/LEARNINGS.md has {n} bytes: move lines that only some tickets need to docs/PITFALLS.md"
