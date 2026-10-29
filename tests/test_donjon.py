"""game/build.py: a Sicilian player builds the Donjon; it shoots and trains units (#1873). Fake server."""
from test_build_site import Server
from test_gather import grid
from test_krepost import DOWN

from game import build, gather, train


def test_a_complete_donjon_shoots_and_trains_the_serjeant_and_the_spearman_line():
    data = grid([[64] * 48 for _ in range(48)], [])
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"civ": "SICILIANS", "color": "blue", "arch": "western"}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (30.5, 64.0, 30.5)}},
                    chosen=build.MENU.index("DONJON") + 1)
    g = gather.Gather(server, data, carry=5, chop=0.25).setup()
    g.stock.update(wood=100, stone=200)
    g.click("Steve")
    site, = g.sites
    cost = build.COSTS["DONJON"]
    assert (g.stock["wood"], g.stock["stone"]) == (100 - cost.get("wood", 0), 200 - cost.get("stone", 0))
    g.select("v0")
    g.click("Steve")
    for _ in range(6000):
        g.step()
        if site["progress"] == 1:
            break
    assert site["progress"] == 1
    shot = [c for c in server.log if c.startswith("aoe building ") and len(c.split()) > 12]   # with its attack
    assert shot, [c for c in server.log if c.startswith("aoe building")]
    assert "DONJON" in train.homes(g).values() and train.trains(g, "DONJON")
