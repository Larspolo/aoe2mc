"""The middle beam of a timber room runs along each wall, like the top beam (#3097): log ends do not show outside."""
import aoe2mc
import buildings

W, H = 12, 6


def beam_axes(wall):
    """The axis of each beam block of the middle row on one wall (posts of the room are not beams)."""
    c = buildings.Canvas(aoe2mc.B, W, height=20)
    c.timber_room(0, W, 0, W, 0, H, buildings.ARCH["western"])
    cells = {"north": [(x, 0) for x in range(1, W - 1)], "south": [(x, W - 1) for x in range(1, W - 1)],
             "west": [(0, z) for z in range(1, W - 1)], "east": [(W - 1, z) for z in range(1, W - 1)]}[wall]
    names = [aoe2mc.B.states[c.get(x, H // 2, z)] for x, z in cells]
    return {n.split("axis=")[1].rstrip("]") for n in names if "stripped" in n}


def test_middle_beam_has_the_axis_of_its_wall():
    assert beam_axes("north") == {"x"}
    assert beam_axes("south") == {"x"}
    assert beam_axes("west") == {"z"}
    assert beam_axes("east") == {"z"}
