"""circle_radius and set_circular_base of create_player_lands in a random map script (#4420)."""
import rmap

SCRIPT = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands {{ terrain_type DIRT land_percent 20 base_size 5 {extra} }}
"""


def lands(extra, seed=1, players=4):
    warns = []
    d = rmap.generate(SCRIPT.format(extra=extra), seed, players, size=100, warn=warns.append)
    return d, {st["player"]: (st["x"], st["y"]) for st in d["lands"]}, warns


def gaps(at):
    return [((x - 49.5) ** 2 + (y - 49.5) ** 2) ** 0.5 for x, y in at.values()]


def test_circle_radius_puts_the_origins_on_its_circle():
    _, at, warns = lands("circle_radius 20 0")
    assert all(abs(g - 20) <= 1 for g in gaps(at)) and not warns


def test_with_no_circle_radius_the_distance_stays_ring():
    _, at, _ = lands("")
    assert all(abs(g - rmap.RING * 100) <= 1 for g in gaps(at))


def test_the_random_change_stays_in_its_band():
    _, at, warns = lands("circle_radius 20 5")
    assert all(15 - 1 <= g <= 25 + 1 for g in gaps(at)) and not warns


def test_set_circular_base_has_no_corners_of_the_square():
    cells = set(rmap.square((50, 50), 5, 100, circular=True))
    assert not cells & {(45, 45), (45, 55), (55, 45), (55, 55)} and (50, 45) in cells
    _, _, warns = lands("set_circular_base")
    assert not warns


def test_the_same_map_for_the_same_seed():
    a, _, _ = lands("circle_radius 30 5 set_circular_base", seed=7)
    b, _, _ = lands("circle_radius 30 5 set_circular_base", seed=7)
    assert a["terrain"] == b["terrain"] and a["lands"] == b["lands"]
