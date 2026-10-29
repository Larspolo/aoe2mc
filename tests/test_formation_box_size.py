"""game/replay.py formation_cells: the Box formation is large enough for all weak units inside the square (#3640)."""
import test_gather  # noqa: F401  (the game modules on sys.path)

from game import replay


def box(militia, archers, knights):
    group = [(f"m{k}", 10.0 + k, 40.0, 1, False) for k in range(militia)]
    group += [(f"a{k}", 10.0 + k, 42.0, 2, True) for k in range(archers)]
    group += [(f"k{k}", 10.0 + k, 44.0, 0, False) for k in range(knights)]
    return replay.formation_cells(lambda x, z: True, group, (20.5, 10.5), "Box")


def inside(out):
    strong = [c for u, c in out.items() if not u.startswith("a")]
    xs, zs = [c[0] for c in strong], [c[1] for c in strong]
    return {u: min(xs) < c[0] < max(xs) and min(zs) < c[1] < max(zs) for u, c in out.items() if u.startswith("a")}


def test_each_archer_stands_inside_the_square_of_the_others():
    out = box(6, 4, 2)
    assert len(out) == 12 and len(set(out.values())) == 12
    assert all(inside(out).values()), out


def test_a_small_group_keeps_a_small_box():
    out = box(8, 1, 0)
    assert all(inside(out).values())
    xs, zs = [c[0] for c in out.values()], [c[1] for c in out.values()]
    assert max(xs) - min(xs) <= 2 * replay.FORMATION + 1 and max(zs) - min(zs) <= 2 * replay.FORMATION + 1
