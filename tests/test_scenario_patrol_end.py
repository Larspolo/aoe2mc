"""#2674 (epic #2538): a new order of a person ends the trigger patrol of a unit, as in AoE2 DE. The patrol tag of
scenario.orders goes from the unit, so the next leg (`aoe moveto @e[tag=...]`) does not walk it back."""
from test_move_order import moves, setup


def test_a_move_order_removes_the_patrol_tag_of_the_units():
    server, g = setup(villagers=0)
    g.patrols = [["aoe_order7_0", [[1, 64, 1], [9, 64, 9]], 0]]
    g.choose({"m0", "m1"}, "m0")
    server.log.clear()
    to = g.walk_to("Steve", (10, 12))
    assert set(moves(server)) == set(to) == {"m0", "m1"}
    assert {c for c in server.log if c.startswith("tag ")} == {"tag m0 remove aoe_order7_0", "tag m1 remove aoe_order7_0"}
    assert "tag m2 remove aoe_order7_0" not in server.log            # a unit that the person did not order patrols on


def test_an_attack_order_removes_the_patrol_tag():
    server, g = setup(villagers=0)
    g.patrols = [["aoe_order7_0", [[1, 64, 1], [9, 64, 9]], 0]]
    g.choose({"m0"}, "m0")
    server.log.clear()
    g.attack("enemy")
    assert "tag m0 remove aoe_order7_0" in server.log


def test_a_game_with_no_trigger_patrol_sends_no_new_command():
    server, g = setup()
    g.choose({"m0", "v0"}, "m0")
    server.log.clear()
    g.walk_to("Steve", (10, 12))
    g.choose({"m0"}, "m0")
    g.attack("enemy")
    assert not any(c.startswith("tag ") and "aoe_order" in c for c in server.log)
