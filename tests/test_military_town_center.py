"""game/train.py, game/regen.py: an Achaemenid town center becomes a Military Town Center (AoE2 DE wiki "Military Town
Center", update 153015): the own military units in its aura range heal and walk faster (the "aura" of its data line).
A town center takes one upgrade of this kind (#2484, #2496). The values come from the data."""
import json

import pytest
from menu_line import item
from test_gather import grid
from test_loom import menus
from test_monk_heal import HealServer

import buildings
from game import ai, build, gather, regen, savegame, train

A, B = (2, 5, 2, 5), (44, 47, 44, 47)                                 # the block footprints of the two town centers
UPGRADE = "MILITARY_TOWN_CENTER"
ROW = next(r for r in train.ROWS if r["name"] == UPGRADE)
AURA, CIV = ROW["aura"], ROW["civs"][0]
OTHER = next(c for c in sorted(buildings.CIV_TO_ARCH) if c not in ROW["civs"])
R = AURA["range"]


def setup(civ=CIV, age=tuple(build.AGE_TECHS[:ROW["age"]])):
    """A flat 50 × 50 map (tile size 1) with two town centers of player 1, a militia "m" in the aura range of town
    center A, a militia "far" out of the range of both, a villager "v" next to A and an enemy militia "foe" next to A."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [45.5, 45.5], "footprint": [44, 44, 47, 47]}]
    ents = {}
    for uuid, name, player, x in (("m", "MILITIA", 1, R - 0.5), ("far", "MILITIA", 1, R + 9.5), ("v", "VILLAGER_MALE", 1, 7.5),
                                  ("foe", "MILITIA", 2, 8.5)):
        objects.append({"kind": "unit", "name": name, "player": player, "uuid": uuid, "tile": [x, 3.5]})
        ents[uuid] = {"Pos": (x, 64.0, 3.5), "Health": 10.0, "Max": 40.0}
    data = grid([[64] * 50 for _ in range(50)], objects)
    data["players"] = {"1": {"civ": civ}, "2": {"civ": OTHER}}
    server = HealServer(ents)
    g = gather.Gather(server, data).setup()
    g.techs.update(age)
    g.stock.update(wood=1000, gold=1000)
    return server, g


def upgrade(g, rect):
    assert train.queue(g, "Steve", rect[::2], UPGRADE) == rect
    train.tick(g, train.seconds(g, UPGRADE, "TOWN_CENTER"))


def test_only_the_achaemenids_see_it_from_its_age():
    server, g = setup()
    train.open_menu(g, "Steve", A[::2])
    assert item(menus(server)[-1], "Military Town Center").startswith(f"{train.SLOTS[UPGRADE]}:book:")
    _, g = setup(age=())
    assert train.queue(g, "Steve", A[::2], UPGRADE) is None                         # not before its age
    server, g = setup(OTHER)
    train.open_menu(g, "Steve", A[::2])
    assert item(menus(server)[-1], "Military Town Center") is None
    assert train.queue(g, "Steve", A[::2], UPGRADE) is None


def test_it_heals_the_own_military_units_in_its_range():
    server, g = setup()
    regen.tick(g, 60.0)
    assert all(e["Health"] == 10.0 for e in server.entities.values())               # no upgrade: no heal
    upgrade(g, A)
    assert g.upgraded == {A: UPGRADE} and UPGRADE not in g.techs                    # only this town center
    regen.tick(g, 60.0)                                                             # one AoE2 minute
    hp = {u: e["Health"] for u, e in server.entities.items()}
    assert hp["m"] == pytest.approx(10.0 + AURA["heal"])
    assert hp["far"] == hp["v"] == hp["foe"] == 10.0                    # out of range, a villager, an enemy


def test_the_units_near_it_walk_faster_and_slow_down_when_they_leave():
    server, g = setup()
    upgrade(g, A)
    base = train.speed(g, "MILITIA")
    server.log.clear()
    regen.tick(g, regen.EVERY)
    fast = AURA["speed"]
    assert g.hurried == {"m": fast}
    assert train.speed(g, "MILITIA", "m") == pytest.approx(fast * base) and train.speed(g, "MILITIA", "far") == base
    assert server.log.count(ai.speed_command("m", "MILITIA", 1, gather.NORMAL * fast * base)) == 1
    server.entities["m"]["Pos"] = (R + 14.5, 64.0, 3.5)                             # out of range
    server.log.clear()
    regen.tick(g, regen.EVERY)
    assert g.hurried == {} and ai.speed_command("m", "MILITIA", 1, gather.NORMAL * base) in server.log
    server.log.clear()
    regen.tick(g, regen.EVERY)
    assert not any("movement_speed" in c for c in server.log)                       # no change: no command


def test_the_upgrade_of_the_other_town_center_stays_its_own():
    server, g = setup()
    upgrade(g, A)
    train.open_menu(g, "Steve", A[::2])
    menu = menus(server)[-1]
    assert item(menu, "Military Town Center") is None and item(menu, "Economic Town Center") is None
    assert train.queue(g, "Steve", A[::2], "ECONOMIC_TOWN_CENTER") is None
    g.stock.update(food=1000)
    assert train.queue(g, "Steve", B[::2], "ECONOMIC_TOWN_CENTER") == B
    train.tick(g, train.seconds(g, "ECONOMIC_TOWN_CENTER", "TOWN_CENTER"))
    assert g.upgraded == {A: UPGRADE, B: "ECONOMIC_TOWN_CENTER"}
    assert g.aura_rate(g.villagers["v"], "wood") == 1                               # a military one: no work bonus


def test_a_save_keeps_it():
    server, g = setup()
    upgrade(g, A)
    _, h = setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g))))
    assert h.upgraded == {A: UPGRADE}
