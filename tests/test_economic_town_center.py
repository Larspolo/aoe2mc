"""game/train.py, game/gather.py: an Achaemenid town center becomes an Economic Town Center: the villagers near it
gather faster (the key "aura" of its line in game/data/train.jsonl). A town center takes one upgrade of this kind;
another town center can take its own (#2484)."""
import json

import pytest
from menu_line import item
from test_gather import FakeServer, grid
from test_loom import menus

from game import gather, savegame, train

A, B = (2, 5, 2, 5), (24, 27, 24, 27)                                 # the block footprints of the two town centers
UPGRADE = "ECONOMIC_TOWN_CENTER"
ROW = next(r for r in train.ROWS if r["name"] == UPGRADE)
RATE, NEAR = ROW["aura"]["rate"], ROW["aura"]["range"]


def setup(civ="ACHAEMENIDS", age=("FEUDAL_AGE",)):
    """A flat 32 × 32 map (tile size 1) with two town centers of player 1 and a villager next to each one."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [25.5, 25.5], "footprint": [24, 24, 27, 27]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "a", "tile": [7.5, 3.5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "b", "tile": [29.5, 25.5]}]
    data = grid([[64] * 32 for _ in range(32)], objects)
    data["players"] = {"1": {"civ": civ}}
    server = FakeServer({"a": {"Pos": (7.5, 64.0, 3.5)}, "b": {"Pos": (29.5, 64.0, 25.5)}})
    g = gather.Gather(server, data).setup()
    g.techs.update(age)
    g.stock.update(food=1000, wood=1000)
    return server, g


def upgrade(g, rect):
    assert train.queue(g, "Steve", rect[::2], UPGRADE) == rect
    train.tick(g, ROW["time"])


def test_villagers_near_the_upgraded_town_center_work_faster():
    _, g = setup()
    a, b = g.villagers["a"], g.villagers["b"]
    assert g.aura_rate(a, "wood") == g.aura_rate(b, "wood") == 1
    upgrade(g, A)
    assert g.upgraded == {A: UPGRADE} and UPGRADE not in g.techs                    # only this town center
    assert g.aura_rate(a, "wood") == g.aura_rate(a, "gold") == g.aura_rate(a, "farm") == pytest.approx(RATE)
    assert g.aura_rate(b, "wood") == 1                                              # near the other town center
    a.pos = (2 + 3 + NEAR + 0.5, 64.0, 3.5)                                         # out of its range
    assert g.aura_rate(a, "wood") == 1


def test_a_town_center_takes_one_upgrade_and_the_other_one_its_own():
    server, g = setup()
    upgrade(g, A)
    train.open_menu(g, "Steve", A[::2])
    assert item(menus(server)[-1], "Economic Town Center") is None
    assert train.queue(g, "Steve", A[::2], UPGRADE) is None
    train.open_menu(g, "Steve", B[::2])
    assert item(menus(server)[-1], "Economic Town Center") is not None
    upgrade(g, B)
    assert g.upgraded == {A: UPGRADE, B: UPGRADE}


def test_a_queued_upgrade_blocks_a_second_one_at_the_same_town_center():
    _, g = setup()
    assert train.queue(g, "Steve", A[::2], UPGRADE) == A
    assert train.queue(g, "Steve", A[::2], UPGRADE) is None
    assert train.queue(g, "Steve", B[::2], UPGRADE) == B                            # another town center: yes


def test_a_save_keeps_the_upgraded_town_centers():
    _, g = setup()
    upgrade(g, A)
    _, h = setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g))))
    assert h.upgraded == {A: UPGRADE} and h.aura_rate(h.villagers["a"], "wood") == pytest.approx(RATE)
