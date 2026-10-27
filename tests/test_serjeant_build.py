"""game/repair.py: selected Serjeants build an own Donjon site, as in AoE2 DE (#2129, AoE2 wiki "Serjeant (Age of
Empires II)": "Can build and repair Donjons"). They build at the villager rate: the wiki gives no own rate."""
import pytest
from test_serjeant_repair import setup

from game import build, civs, gather, repair

SITE = (12, 14, 5, 7)                                                # block footprint (x0, x1, z0, z1), free ground


def site(g, name="DONJON", rect=SITE):
    g.stock.update(wood=1000, stone=1000)
    g.data.setdefault("level_height", 1)                             # the design of the site
    return build.found(g, name, rect)


def ticks(g, s, limit=5000):
    for n in range(1, limit):
        g.step()
        if s["progress"] >= 1:
            return n
    return None


def test_selected_serjeants_build_an_own_donjon_site_at_the_villager_rate():
    server, g = setup()
    s = site(g)
    g.choose({"s0"}, "s0")
    assert repair.build_order(g, s, g.selected) == ["s0"]
    assert any(c.startswith("aoe moveto s0 ") for c in server.log)  # it walks with the plugin path finding
    assert repair.raisers(g, s) == ["s0"]                            # it stands next to the site
    n = ticks(g, s)
    rate = civs.build_rate(g, "DONJON")                              # the Sicilians build a Donjon faster (#2115)
    assert n == pytest.approx(build.BUILD_TIMES["DONJON"] / rate / gather.NORMAL / g.tick, abs=1)
    assert not repair.raisers(g, s)                                  # complete: the Serjeant stands


def test_a_serjeant_does_not_build_a_house_site():
    server, g = setup()
    s = site(g, "HOUSE")
    g.choose({"s0"}, "s0")
    assert repair.build_order(g, s, g.selected) == []
    for _ in range(50):
        g.step()
    assert s["progress"] == 0


def test_a_move_order_ends_the_build_of_a_serjeant():
    server, g = setup()
    s = site(g)
    g.choose({"s0"}, "s0")
    repair.build_order(g, s, g.selected)
    g.walk_to("Steve", (20, 20))
    for _ in range(50):
        g.step()
    assert s["progress"] == 0
