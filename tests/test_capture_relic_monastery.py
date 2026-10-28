"""#2458: in the mode "Capture the Relic" each player starts with a pre-built, indestructible monastery and cannot
build more monasteries (AoE2 wiki "Capture the Relic"). Map and fake server of test_empire_wars."""
import collections

from test_empire_wars import town_map
from test_relics import setup as relics_setup

from game import build, capture_relic, monk, train


def start():
    g = town_map()
    train.start(g, "castle")                                           # a monastery is a Castle Age building
    g.mode = "capture-the-relic"
    return g


def test_each_player_with_a_town_center_starts_with_one_complete_free_monastery():
    g = start()
    stock = dict(g.stock)
    capture_relic.setup(g)
    sites = [s for s in g.sites if s["name"] == "MONASTERY"]
    assert len(sites) == 1 and sites[0].get("done") and sites[0]["lasting"] and g.stock == stock
    assert set(monk.monasteries(g)) == {sites[0]["footprint"]}         # the center relic can go home there


def test_the_monastery_has_no_target_entity_so_nothing_can_damage_it():
    g = start()
    capture_relic.setup(g)
    site = next(s for s in g.sites if s["name"] == "MONASTERY")
    x0, x1, z0, z1 = site["footprint"]
    assert not any(x0 <= b[0] <= x1 and z0 <= b[2] <= z1 for b in g.forts.values())
    assert not any(c.startswith("aoe building ") for c in g.game.log)
    house = build.found(g, "HOUSE", build.near(g, "HOUSE", (24, 24)))  # another building of the mode keeps its target
    build.rise(g, house, float("inf"))
    assert any(c.startswith("aoe building ") for c in g.game.log)


def test_the_build_menu_refuses_a_monastery_only_in_the_mode():
    g = start()
    assert build.locked(g, "MONASTERY") == "Capture the Relic: no more monasteries"
    g.mode = "standard"
    assert build.locked(g, "MONASTERY") is None


def test_a_second_setup_gives_no_second_monastery():
    g = start()
    capture_relic.setup(g)
    capture_relic.setup(g)
    assert collections.Counter(s["name"] for s in g.sites)["MONASTERY"] == 1


def test_a_player_without_a_town_center_gets_no_monastery():
    _, g = relics_setup()                                              # a monk and a monastery of the map, no town center
    capture_relic.setup(g)
    assert "MONASTERY" not in {s["name"] for s in g.sites}
