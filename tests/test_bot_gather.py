"""game/bot.py: a bot of player 2 gathers food, wood, gold and stone (#856). The fast tests use the fake server of
test_gather; the mc test a real one."""
import contextlib
import io
import json
import re
import time

import pytest
from test_gather import FakeServer, grid

from game import bot, gather, run


def bot_map():
    """A flat 32 × 32 map (tile size 1): a town center and a villager of player 1, a town center and five villagers
    of player 2, trees, a fruit bush, a gold mine and a stone mine near player 2."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "p1", "tile": [6.5, 6.5]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 2, "footprint": [20, 20, 23, 23]},
               {"kind": "other", "name": "TREE_OAK", "tile": [26.5, 21.5]},
               {"kind": "other", "name": "TREE_OAK", "tile": [27.5, 21.5]},
               {"kind": "other", "name": "FRUIT_BUSH", "tile": [21.5, 26.5]},
               {"kind": "other", "name": "GOLD_MINE", "tile": [16.5, 21.5]},
               {"kind": "other", "name": "STONE_MINE", "tile": [21.5, 16.5]}]
    pos = {"p1": {"Pos": (6.5, 64.0, 6.5)}}
    for i in range(5):
        objects.append({"kind": "unit", "name": "VILLAGER_FEMALE", "player": 2, "uuid": f"b{i}", "tile": [24.5, 19.5 + i]})
        pos[f"b{i}"] = {"Pos": (24.5, 64.0, 19.5 + i)}
    server = FakeServer(pos)
    command, at = server.command, []

    def track(cmd):                                                    # a trained unit gets a position (#858)
        if m := re.match(r"summon \S+ (\S+) (\S+) (\S+) ", cmd):
            at[:] = [tuple(map(float, m.groups()))]
        elif (m := re.match(r"aoe stats (\S+) ", cmd)) and at and m[1] not in server.entities:
            server.entities[m[1]] = {"Pos": at[0], "Rotation": (0.0, 0.0)}
        return command(cmd)
    server.command = track
    data = grid([[64] * 32 for _ in range(32)], objects)
    data.update(level_height=1, players={"2": {"color": "blue", "arch": "western"}})   # the bot builds too (#857)
    me = gather.Gather(server, data, carry=10, chop=0.05, start={}).setup()
    return server, me, bot.Bot(server, data, share=me, carry=10, chop=0.05, start={}).setup()


def test_the_bot_gathers_all_four_resources():
    server, me, b = bot_map()
    assert set(b.g.villagers) == {f"b{i}" for i in range(5)} and set(me.villagers) == {"p1"}
    for _ in range(3000):
        b.step()
        if all(b.g.stock.values()):
            break
    assert all(n > 0 for n in b.g.stock.values()), b.g.stock
    work = sorted(v.res for v in b.g.villagers.values())
    assert work == ["food", "food", "gold", "stone", "wood"]          # the shares of bot.SHARE, food first
    drops = [c for c in server.log if c.startswith("scoreboard players add") and c.split()[-1] != "0"]
    assert drops and all(c.split()[4] == "aoe_res2" for c in drops)    # no point goes to the sidebar of player 1


def test_the_sidebar_of_player_1_does_not_change():
    server, me, b = bot_map()
    before = len(server.log)
    for _ in range(500):
        b.step()
    assert not [c for c in server.log[before:] if "aoe_res" in c.split()]
    assert b.g.villagers.keys().isdisjoint(me.villagers) and not me.selected
    assert all(n == 0 for n in me.stock.values())


def test_both_players_use_the_same_resources():
    server, me, b = bot_map()
    tree = (26, 21)
    assert b.g.map.trees is me.map.trees
    me.map.trees[tree] = 0                                             # player 1 felled it
    b.step()
    assert all(v.tree != tree for v in b.g.villagers.values())


def test_a_source_without_a_path_is_skipped():
    server, me, b = bot_map()
    b.step()
    v = next(v for v in b.g.villagers.values() if v.res == "stone")
    stone = v.tree
    b.g.set(v, "idle")                                                 # it found no path to the mine
    b.step()
    assert stone in b.failed and v.tree != stone


@pytest.mark.mc
def test_the_bot_gathers_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(24)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=4, y=4)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=8.5, y=8.5)
    um.add_unit(scenarios.PlayerId.TWO, BuildingInfo.TOWN_CENTER.ID, x=16, y=16)
    for i in range(4):
        um.add_unit(scenarios.PlayerId.TWO, UnitInfo.VILLAGER_FEMALE.ID, x=19.5, y=14.5 + i)
    for name, x, y in (("TREE_OAK_FOREST", 21.5, 17.5), ("FRUIT_BUSH", 17.5, 20.5), ("GOLD_MINE", 12.5, 16.5),
                       ("STONE_MINE", 16.5, 12.5)):
        um.add_unit(scenarios.PlayerId.GAIA, getattr(OtherInfo, name).ID, x=x, y=y)
    src = str(tmp_path / "bot.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        end = time.time() + 60                                         # entities load in other threads
        while True:
            me = gather.Gather(game, data, tick=0.1, carry=3, chop=0.01, start={}).setup()
            b = bot.Bot(game, data, share=me, tick=0.1, carry=3, chop=0.01, start={}).setup()
            if me.villagers and len(b.g.villagers) == 4:
                break
            assert time.time() < end, "the villagers did not load"
            time.sleep(1)
        me.bots = [b]
        me.run(120, until=lambda: all(b.g.stock.values()))
        assert all(n > 0 for n in b.g.stock.values()), b.g.stock
        assert all(n == 0 for n in me.stock.values())
        for r in gather.RESOURCES:                                     # the objective of the bot, not the sidebar
            assert "has 0 " in game.command(f"scoreboard players get {r} aoe_res")
            assert "has 0 " not in game.command(f"scoreboard players get {r} aoe_res2")
