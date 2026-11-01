"""game/gather.py: a right click with selected villagers on a carcass sends them to gather its food (#5536)."""
from test_gather import FakeServer, grid

from game import gather


def test_a_click_on_a_carcass_sends_a_hunter():
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    g = gather.Gather(server, grid([[64] * 20 for _ in range(20)], objects), carry=10, chop=0.25, start={}).setup()
    g.map.carcasses[(10, 10)] = 100
    eye, d = (10.5, 65.62, 14.5), gather.direction(180, 20)            # look north and down at the carcass
    assert g.map.pick_tree(eye, d) == (10, 10)
    g.select("v")
    assert g.target(eye, d, {})[:2] == ("carcass", (10, 10))
    server.entities["Steve"] = {"Pos": (10.5, 64.0, 14.5), "Rotation": (180.0, 20.0)}
    g.click("Steve")
    v = g.villagers["v"]
    assert v.state == "to_tree" and v.res == "food" and v.tree == (10, 10) and v.task == "HUNTER"
    for _ in range(3000):
        g.step()
        if g.stock["food"] > 0:
            break
    assert g.stock["food"] > 0 and g.map.carcasses[(10, 10)] < 100
