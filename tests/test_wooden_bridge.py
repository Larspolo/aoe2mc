"""The wooden bridge looks like the game (#456): boards across the bridge, posts over the deck, no railing."""
import aoe2mc
import buildings


def draw(ctx):
    c = buildings.Canvas(aoe2mc.B, 4, height=40, margin=3, below=12)
    buildings.wooden_bridge(c, 4, None, None, 4, {"deck": 2, **ctx})
    return lambda x, y, z: aoe2mc.B.states[c.get(x, y, z)] if c.get(x, y, z) >= 0 else "air"


def test_boards_cross_the_bridge():
    get = draw({"along_z": False})
    assert get(0, 2, 1).endswith("stripped_spruce_log[axis=z]") and get(1, 2, 1).endswith("spruce_planks")
    get = draw({"along_z": True})
    assert get(1, 2, 0).endswith("stripped_spruce_log[axis=x]") and get(1, 2, 1).endswith("spruce_planks")


def test_posts_on_water_sides_only():
    get = draw({"rails": ["n"]})
    assert [get(x, 3, 0).endswith("stripped_oak_log") for x in range(4)] == [True, False, True, False]
    assert all(get(x, 3, 3).endswith("air") for x in range(4))
