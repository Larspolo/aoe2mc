"""game/bot.py: the soldiers of the bot attack player 1 after a set time (#859)."""
import contextlib
import io
import json
import re
import time

import pytest
from test_bot_gather import bot_map

from game import bot, combat, gather, run


def armed(n=2, attack=60.0, sight=False):
    """bot_map with n militia of player 2 at its town center. The fake server answers `execute if entity` for each
    entity with a position and for the targets of the buildings in `server.forts`. The bot sees the whole map, unless
    sight: then only the AoE2 sight of its units and buildings (#2050)."""
    server, me, b = bot_map()
    if not sight:
        b.g.seen_tiles = lambda *a, **k: {(x, z) for x in range(32) for z in range(32)}
    b.attack, b.group = attack, n                                      # all n soldiers are one wave (#1051)
    for i in range(n):
        u = f"m{i}"
        server.entities[u] = {"Pos": (19.5, 64.0, 24.5 + i), "Rotation": (0.0, 0.0)}
        b.g.soldiers[u] = "MILITIA"
    server.forts = set()
    command = server.command

    def alive(cmd):
        if m := re.fullmatch(r"execute if entity (\S+)", cmd):
            return "Test passed" if m[1] in server.entities or m[1] in server.forts else "Test failed"
        return command(cmd)
    server.command = alive
    return server, me, b


def orders(server, start=0):
    return [c.split()[2:] for c in server.log[start:] if c.startswith("aoe attack ")]


def steps(b, seconds):
    """Steps of the bot for this many AoE2 seconds."""
    for _ in range(round(seconds / (b.g.tick * gather.NORMAL))):
        b.step()


def test_the_soldiers_wait_until_the_attack_time():
    server, me, b = armed(attack=60.0)
    steps(b, 59)
    assert orders(server) == []
    steps(b, 2)
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"]]      # the only unit of player 1


def test_the_soldiers_attack_the_nearest_unit_of_player_1():
    server, me, b = armed(attack=0.0)
    me.villagers["far"] = me.villagers["p1"]
    server.entities["far"] = {"Pos": (1.5, 64.0, 1.5)}
    server.entities["p1"]["Pos"] = (12.5, 64.0, 24.5)
    b.fight()
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"]]


def test_a_new_target_when_the_target_dies():
    server, me, b = armed(attack=0.0)
    me.soldiers["s1"] = "ARCHER"                                       # a unit that player 1 trained
    server.entities["s1"] = {"Pos": (2.5, 64.0, 2.5)}
    b.fight()
    assert {t for _, t in orders(server)} == {"p1"}
    n = len(server.log)
    b.fight()
    assert orders(server, n) == []                                     # a live target: no new order
    del server.entities["p1"]
    b.fight()
    assert sorted(orders(server, n)) == [["m0", "s1"], ["m1", "s1"]]


def test_with_no_unit_left_the_soldiers_attack_a_building():
    server, me, b = armed(attack=0.0)
    del server.entities["p1"]
    tc = combat.target_uuid([2, 2, 5, 5])                              # the town center of player 1
    server.forts.add(tc)
    b.fight()
    assert sorted(orders(server)) == [["m0", tc], ["m1", tc]] and tc in b.g.sieged
    server.forts.discard(tc)
    n = len(server.log)
    b.fight()
    assert orders(server, n) == []                                     # nothing left to attack


def test_a_step_sends_the_attack_after_the_time():
    server, me, b = armed(attack=1.0)
    b.step()
    assert orders(server) == []
    steps(b, 1.5)
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"]]


@pytest.mark.mc
def test_two_soldiers_of_the_bot_attack_on_a_server(tmp_path):
    """Two militia of the bot kill the villager of player 1, then attack its town center."""
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    from test_building_damage import hp

    import aoe2mc
    scn = scenarios.new_scenario(24)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=4, y=4)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=10.5, y=10.5)
    um.add_unit(scenarios.PlayerId.TWO, BuildingInfo.TOWN_CENTER.ID, x=18, y=18)
    for i in range(2):
        um.add_unit(scenarios.PlayerId.TWO, UnitInfo.MILITIA.ID, x=14.5, y=13.5 + i)
    src = str(tmp_path / "attack.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    tc = next(combat.target_uuid(o["footprint"]) for o in data["objects"]
              if o["name"] == "TOWN_CENTER" and o["player"] == 1)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        end = time.time() + 60                                         # entities load in other threads
        while True:
            me = gather.Gather(game, data, tick=0.1, start={}).setup()
            b = bot.Bot(game, data, share=me, tick=0.1, attack=1.0, group=2, start={}).setup()
            if me.villagers and len(b.g.positions(list(b.g.soldiers))) == 2:
                break
            assert time.time() < end, "the units did not load"
            time.sleep(1)
        combat.setup(game, data)
        me.bots = [b]
        (v,) = me.villagers
        full = hp(game, tc)
        me.run(90, until=lambda: me.pos(v) is None and (hp(game, tc) or full) < full)
        assert me.pos(v) is None, "the villager of player 1 lives"
        assert set(b.targets.values()) == {tc} and hp(game, tc) < full, (b.targets, hp(game, tc), full)
