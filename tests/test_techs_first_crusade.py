"""The key "spawn" of data/train.jsonl (#4365, First Crusade of the Sicilians): at the research, each of the first
"most" complete own buildings "at" summons "count" units, the upgraded unit of the line. Test data: a monkeypatched
line of the key (owner, 2026-10-29, #4242), not the values of the data line."""
import math

from test_gather import FakeServer, grid

from game import build, gather, train

TECH = "LOOM"                                                       # train.research needs a real name


def town_centers(own, enemy=0):
    """A flat 40 × 40 map (tile size 1) with own town centers of player 1 and enemy ones of player 2 in one row."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1 + (i >= own), "tile": [3.5 + 8 * i, 3.5],
                "footprint": [2 + 8 * i, 2, 5 + 8 * i, 5]} for i in range(own + enemy)]
    data = grid([[64] * 40 for _ in range(40)], objects) | {"players": {"1": {"civ": "SICILIANS", "color": "blue"},
                                                                        "2": {"civ": "BRITONS", "color": "red"}}}
    server = FakeServer({"Steve": {"Pos": (12.0, 64.0, 20.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, data, start={}).setup()
    g.techs.update(build.AGE_TECHS[:2])
    return server, g, [o["footprint"] for o in objects if o["player"] == 1]


def research(monkeypatch, g, unit="SERJEANT"):
    monkeypatch.setitem(train.BY_KEY["spawn"], TECH, {"unit": unit, "at": "TOWN_CENTER", "count": 2, "most": 3})
    before = set(g.soldiers)
    train.research(g, {"name": TECH, "player": "Steve"})
    return {u: g.soldiers[u] for u in g.soldiers if u not in before}


def near(server, uuid, feet):
    x, _, z = server.entities[uuid]["Pos"]
    return any(math.dist((x, z), ((x0 + x1) / 2, (z0 + z1) / 2)) < 6 for x0, z0, x1, z1 in feet)


def test_each_own_building_summons_its_units(monkeypatch):
    server, g, feet = town_centers(2, enemy=1)
    new = research(monkeypatch, g)
    assert sorted(new.values()) == ["SERJEANT"] * 4
    assert all(near(server, u, feet) for u in new)


def test_at_most_most_buildings_summon(monkeypatch):
    _, g, _ = town_centers(4)
    assert len(research(monkeypatch, g)) == 6


def test_the_upgrade_of_the_line_gives_the_upgraded_unit(monkeypatch):
    _, g, _ = town_centers(1)
    g.techs.add("ELITE_SERJEANT_UPGRADE")
    assert sorted(research(monkeypatch, g).values()) == ["ELITE_SERJEANT"] * 2
