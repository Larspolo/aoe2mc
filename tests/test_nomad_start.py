"""The game program on a --random-map nomad world (#1212): a player without a town center gets the AoE2 Nomad start
resources, a villager builds the first town center, and then the villagers drop resources at it. Fake server."""
import json
import os

import pytest
from test_build_site import Server
from test_gather import FakeServer, grid

import aoe2mc
from game import build, gather

DOWN = (0.0, 90.0)                                                     # yaw, pitch: look straight down


@pytest.fixture(scope="module")
def nomad(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("nomad") / "world")
    aoe2mc.convert(aoe2mc.RANDOM_MAP + "nomad", out, seed=7)
    with open(os.path.join(out, "aoe2mc.json")) as f:
        return json.load(f)


def test_the_nomad_start_is_the_standard_start_and_the_cost_of_a_town_center():
    # AoE2 wiki, "Nomad (map)": "each player starts with an additional 275 wood and 100 stone in order to afford
    # their starting Town Center"
    assert gather.NOMAD == build.COSTS["TOWN_CENTER"]
    units = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0", "tile": [1.5, 1.5]}]
    rows = [[64] * 8 for _ in range(8)]
    g = gather.Gather(FakeServer({}), grid(rows, units))
    assert g.stock == {r: v + gather.NOMAD.get(r, 0) for r, v in gather.START.items()}
    tc = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [4.0, 4.0], "footprint": [2, 2, 6, 6]}
    assert gather.Gather(FakeServer({}), grid(rows, units + [tc])).stock == gather.START       # a standard start
    assert gather.Gather(FakeServer({}), grid(rows, [])).stock == gather.START               # no units: no start
    assert gather.Gather(FakeServer({}), grid(rows, units), start={}).stock["wood"] == 0     # start= wins


def test_a_villager_builds_the_first_town_center_and_drops_wood_at_it(nomad):
    vils = [o for o in nomad["objects"] if o["kind"] == "unit" and o["player"] == 1 and "VILLAGER" in o["name"]]
    assert len(vils) == 3 and not any(o["kind"] == "building" for o in nomad["objects"] if o.get("player") == 1)
    m, T = gather.Map(nomad), nomad["tile_size"]
    pos = {v["uuid"]: (int(v["tile"][0] * T), int(v["tile"][1] * T)) for v in vils}
    cx, cz = (round(sum(p[i] for p in pos.values()) / 3) for i in (0, 1))   # the free place between the villagers
    entities = {u: {"Pos": (x + 0.5, m.y(x, z), z + 0.5)} for u, (x, z) in pos.items()}
    entities["Steve"] = {"Pos": (cx + 0.5, m.y(cx, cz), cz + 0.5), "Rotation": DOWN}
    server = Server(entities, chosen=build.MENU.index("TOWN_CENTER") + 1)
    g = gather.Gather(server, nomad, carry=5, chop=0.25).setup()
    start = {r: v + gather.NOMAD.get(r, 0) for r, v in gather.START.items()}
    assert (g.stock["wood"], g.stock["stone"]) == (start["wood"], start["stone"])
    g.click("Steve")
    site, = g.sites
    assert site["name"] == "TOWN_CENTER" and (g.stock["wood"], g.stock["stone"]) == (gather.START["wood"], gather.START["stone"])
    builder = min(pos, key=lambda u: (pos[u][0] - cx) ** 2 + (pos[u][1] - cz) ** 2)
    g.select(builder)
    g.click("Steve")
    for _ in range(6000):
        g.step()
        if site["progress"] == 1:
            break
    assert site["progress"] == 1
    x0, x1, z0, z1 = site["footprint"]
    cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    assert {r for r, sites in g.map.drops.items() if cells in sites} == set(gather.DROP_SITES)
    tree = min(g.map.trees, key=lambda t: (t[0] * T - cx) ** 2 + (t[1] * T - cz) ** 2)
    g.send(tree)
    v, dropped = g.villagers[builder], False
    for _ in range(4000):
        g.step()
        dropped |= v.state == "to_drop" and not v.path and v.cell in g.map.around(cells)
        if server.wood() >= 10:
            break
    assert dropped and server.wood() >= 10 and g.stock["wood"] == gather.START["wood"] + server.wood()
