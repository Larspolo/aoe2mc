"""game/monk.py: a heal pass that adds hit points shows heart particles at the eyes of the healed unit (#1634).
Fake server, no Minecraft."""
from test_monk_heal import run, setup


def hearts(server):
    return [c.split()[2] for c in server.log if c.startswith("execute at ") and "particle minecraft:heart" in c]


def test_each_heal_pass_shows_hearts_at_the_healed_unit():
    server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0))
    run(g, 4)
    assert hearts(server) == ["a"] * 4
    assert "execute at a anchored eyes run particle minecraft:heart ^ ^ ^ 0.3 0.3 0.3 0 2" in server.log


def test_no_hearts_at_full_health_out_of_range_or_without_a_monk_heal():
    server, g = setup(("full", "MILITIA", 1, 6.5, 40.0, 40.0), ("far", "MILITIA", 1, 9.6, 10.0, 40.0),
                      ("foe", "MILITIA", 2, 7.5, 10.0, 40.0))
    run(g, 10)
    assert hearts(server) == []
    server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0))
    run(g, 60)                                                          # healed to full: the hearts stop
    n = len(hearts(server))
    run(g, 10)
    assert n == 12 and len(hearts(server)) == n
