"""game/train.py: a click on the own town center queues a villager for its food; it appears after the AoE2 train
time next to the town center and can gather (#612)."""
import contextlib
import io
import json
import re
import time

import pytest
from test_gather import FakeServer, grid

from game import combat, gather, run, train

FOOD = train.COSTS["VILLAGER_MALE"]["food"]


def setup(food=60):
    """A flat 24 × 24 map (tile size 1): a town center of player 1 at blocks x 2-4, z 2-4, one of player 2, a tree
    and a villager. The player Steve stands south of the own town center and looks at it."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 2, "tile": [18.5, 18.5],
                "footprint": [17, 17, 20, 20]},
               {"kind": "other", "name": "TREE_OAK", "tile": [20.5, 4.5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}, "Steve": {"Pos": (3.5, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), start={}).setup()
    g.stock["food"] = food
    server.scores["aoe_use"] = 1
    return server, g


def test_a_click_on_the_town_center_queues_a_villager_and_takes_its_food():
    server, g = setup(food=FOOD + 10)
    for name in g.clicks():
        g.click(name)                                                  # opens the menu of the town center (#620)
    server.scores["aoe_menu"] = 1                                      # a click on the villager item
    g.clicks()
    assert g.stock["food"] == 10 and f"scoreboard players remove Food aoe_res {FOOD}" in server.log
    assert g.queues == {(2, 5, 2, 5): [{"name": "VILLAGER_MALE", "progress": 0.0, "player": "Steve"}]}
    server.scores["aoe_menu"] = 1                                      # 10 food: no second villager
    g.clicks()
    assert g.stock["food"] == 10 and len(g.queues[2, 5, 2, 5]) == 1
    assert any(c.startswith("tellraw Steve") and f"{FOOD} food" in c for c in server.log)


def test_no_queue_at_the_town_center_of_another_player_or_on_the_ground():
    server, g = setup()
    assert train.queue(g, "Steve", (18, 18)) is None and train.queue(g, "Steve", (10, 10)) is None
    assert g.stock["food"] == 60 and not g.queues


def test_the_queue_holds_15_units():
    server, g = setup(food=FOOD * (train.QUEUE + 1))
    assert all(train.queue(g, "Steve", (3, 3)) for _ in range(train.QUEUE))
    assert train.queue(g, "Steve", (3, 3)) is None and g.stock["food"] == FOOD


def test_the_villager_appears_after_its_train_time_in_front_of_the_town_center():
    server, g = setup(food=2 * FOOD)
    train.queue(g, "Steve", (3, 3))
    train.queue(g, "Steve", (3, 3))
    steps = round(train.TRAIN_TIMES["VILLAGER_MALE"] / (g.tick * gather.NORMAL))
    for _ in range(steps - 1):
        g.step()
    assert not [c for c in server.log if c.startswith("summon")]
    g.step()
    summon, = [c for c in server.log if c.startswith("summon")]
    m = re.match(r"summon minecraft:villager (\S+) (\S+) (\S+) ", summon)
    assert m and (float(m[1]), float(m[2]), float(m[3])) == (3.5, 64.0, 5.5)   # south of the middle
    assert len(g.villagers) == 2 and len(g.units) == 2 and len(g.queues[2, 5, 2, 5]) == 1
    new = next(v for u, v in g.villagers.items() if u != "v")
    assert "UUID:[I;" in summon and any(c.startswith(f"aoe stats {new.uuid} ") for c in server.log)
    server.entities[new.uuid] = {"Pos": new.pos}                       # alive: the census keeps it (#1039)
    for _ in range(steps):                                             # the second one takes the next cell
        g.step()
    assert len(g.villagers) == 3 and not g.queues[2, 5, 2, 5]
    assert len({v.cell for v in g.villagers.values()}) == 3


def test_a_trained_villager_can_be_selected_and_gather():
    server, g = setup()
    train.queue(g, "Steve", (3, 3))
    new, = train.tick(g, train.TRAIN_TIMES["VILLAGER_MALE"])
    g.select(new.uuid)
    g.send((20, 4))
    assert new.tree == (20, 4) and new.state == "to_tree" and new.path


@pytest.mark.mc
def test_a_trained_villager_chops_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo

    import aoe2mc
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=4, y=4)
    scn.unit_manager.add_unit(scenarios.PlayerId.GAIA, OtherInfo.TREE_OAK_FOREST.ID, x=10.5, y=4.5)
    src = str(tmp_path / "train.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data, tick=0.25, carry=3, chop=0.25, start={}).setup()
        g.stock["food"] = FOOD
        assert train.queue(g, "nobody", (4 * 4 + 1, 4 * 4 + 1))
        new, = train.tick(g, train.TRAIN_TIMES["VILLAGER_MALE"])
        assert g.pos(new.uuid), "the trained villager exists"
        assert "Stats: 1 units" in game.command(combat.stats_command(new.uuid, "VILLAGER_MALE"))
        g.select(new.uuid)
        g.send(min(g.map.trees))
        end = time.time() + 120
        while not g.stock["wood"]:
            assert time.time() < end, "no wood after 120 s"
            g.step()
        assert g.pos(new.uuid)
