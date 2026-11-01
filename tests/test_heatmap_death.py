"""The death heat map of the live replay (#5458): the parse of "aoe deathmarks heat" and its grid."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "game"))
import heatmap  # noqa: E402


def test_parse_gives_grid_per_player():
    counts = heatmap.death_counts("Deaths: p1 2 3 4 p2 0 0 1 p1 2 3 1 gaia 1 1 5 p1 99 0 2")
    assert counts == {(1, 2, 3): 5, (2, 0, 0): 1, (1, 99, 0): 2}
    g = heatmap.grid(counts, {}, 8, "death")
    assert sorted(g) == [1, 2] and g[1][2, 3] == 5 and g[1].sum() == 5 and g[2][0, 0] == 1


def test_empty_answer():
    assert heatmap.death_counts("Deaths:") == {} and heatmap.grid({}, {}, 4, "death") == {}
    assert heatmap.death_counts("Unknown command") == {}
