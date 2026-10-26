"""game/gather.py: the sidebar shows the number of idle villagers of player 1, as the idle villager button of AoE2
(#744). The value is sent only when it changes."""
from test_gather import FakeServer, grid

from game import gather


def setup():
    """A flat 24 × 24 map (tile size 1): a town center of player 1, a tree and 3 villagers."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "other", "name": "TREE_OAK", "tile": [15.5, 15.5]}]
    objects += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": u, "tile": [p, p]}
                for u, p in (("a", 7.5), ("b", 9.5), ("c", 11.5))]
    server = FakeServer({u: {"Pos": (p, 64.0, p)} for u, p in (("a", 7.5), ("b", 9.5), ("c", 11.5))})
    return server, gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()


def idle(server):
    return [c for c in server.log if c.startswith("scoreboard players set Idle aoe_res ")]


def test_idle_villagers_in_the_sidebar():
    server, g = setup()
    assert 'scoreboard players display name Idle aoe_res "Idle villagers"' in server.log
    assert idle(server) == ["scoreboard players set Idle aoe_res 3"]
    tree, = g.map.trees
    g.select("a")
    g.send(tree)
    g.step()
    assert idle(server)[-1] == "scoreboard players set Idle aoe_res 2"
    for _ in range(5):
        g.step()
    assert len(idle(server)) == 2                                      # no command when the value stays


def test_a_builder_of_a_complete_site_is_idle(monkeypatch):
    server, g = setup()
    site = {"name": "HOUSE", "player": 1, "footprint": [16, 18, 2, 4], "progress": 0.9}
    g.sites.append(site)
    v = g.villagers["b"]
    v.site, v.state = site, "build"
    monkeypatch.setattr(gather.build, "rise", lambda g, site, work: False)
    g.step()
    assert idle(server)[-1] == "scoreboard players set Idle aoe_res 2"
    monkeypatch.setattr(gather.build, "rise", lambda g, site, work: True)    # the site is complete
    g.step()
    assert v.state == "idle" and idle(server)[-1] == "scoreboard players set Idle aoe_res 3"
