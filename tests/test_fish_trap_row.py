"""game/gather.py and game/fleet.py: a fishing ship that completes a fish trap of a row of sneak clicks builds the next
trap of the row, and after the last one it fishes (#3114). Fake server, no Minecraft."""
from test_fish_trap import TRAP, feudal

from game import build, fleet

NEXT = (14, 17, 5, 8)                                                  # the next trap of the row: next to the shore


def test_a_ship_builds_each_trap_of_its_row_and_then_fishes():
    server, g, uuid = feudal()
    v = g.ships[uuid]
    first = build.found(g, "FISH_TRAP", TRAP)
    second = build.found(g, "FISH_TRAP", NEXT)
    first["row"] = second["row"] = "row"
    assert fleet.build_site(g, {uuid}, second) == {uuid}
    for _ in range(3000):
        g.step()
        if first["progress"] >= 1 and second["progress"] >= 1:
            break
    assert first["progress"] >= 1 and second["progress"] >= 1
    assert v.state in ("to_tree", "chop") and v.tree == fleet.trap(g, first)


def test_no_ship_keeps_the_build_state_on_a_complete_site():
    server, g, uuid = feudal()
    v = g.ships[uuid]
    first = build.found(g, "FISH_TRAP", TRAP)
    second = build.found(g, "FISH_TRAP", NEXT)
    first["row"] = second["row"] = "row"
    fleet.build_site(g, {uuid}, second)
    for _ in range(6000):
        g.step()
    assert v.state != "build" or v.site is not second
    assert v.site is None or v.site["progress"] < 1
