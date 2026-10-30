"""The fog of war for the enemy units in the game program (#1389): the hide and show commands of one update."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import fog  # noqa: E402
import gather  # noqa: E402

T = 4
E1, E2 = "00000000-0000-0000-0000-00000000000e", "00000000-0000-0000-0000-00000000000f"


def bare(players=None, player=1, enemies=None, villagers=("v",)):
    g = gather.Gather.__new__(gather.Gather)
    g.player, g.data, g.map, g.paper = player, {"objects": []}, types.SimpleNamespace(T=T), True
    g.villagers, g.soldiers, g.sites = dict.fromkeys(villagers), {}, []
    g.enemies = {E1: "MILITIA", E2: "ARCHER"} if enemies is None else enemies
    g.players, g.bots, g.sent, g.now = players or {}, [], [], 0.0
    g.command, g.clock = g.sent.append, lambda: g.now
    return g


def at(x, y):
    return (x + 0.5) * T, 70.0, (y + 0.5) * T


def test_an_enemy_out_of_sight_hides_and_shows_again_in_sight():
    g, far = bare(), 10 + combat.sight("VILLAGER") + 3
    assert fog.update(g, {"v": at(10, 10), E1: at(far, 10), E2: at(11, 10)}) == [f"aoe hide @a[team=p1] {E1}"]
    assert fog.update(g, {"v": at(10, 10), E1: at(far, 10), E2: at(11, 10)}) == []     # only the changes
    assert fog.update(g, {"v": at(far - 1, 10), E1: at(far, 10), E2: at(far - 2, 10)}) == [f"aoe show @a[team=p1] {E1}"]


def test_a_dead_hidden_unit_gives_no_command():
    g = bare()
    fog.update(g, {"v": at(10, 10), E1: at(60, 10), E2: at(60, 12)})
    assert fog.update(g, {"v": at(60, 11), E2: at(60, 12)}) == [f"aoe show @a[team=p1] {E2}"]   # E1 died
    assert E1 not in g.fog["hidden"]


def test_the_units_of_an_ally_see_and_an_ally_is_not_hidden():
    teams = {"1": {"team": 1}, "2": {"team": 1}, "3": {}}
    g = bare(teams, enemies={E1: "MILITIA"})
    ally, foe = bare(teams, player=2, villagers=("a",)), bare(teams, player=3, villagers=(E2,))
    g.bots = [types.SimpleNamespace(g=ally), types.SimpleNamespace(g=foe)]
    out = fog.update(g, {"v": at(10, 10), "a": at(80, 10), E1: at(81, 10), E2: at(10, 80)})
    assert out == [f"aoe hide @a[team=p1] {E2}"]                   # E1 is in the sight of the ally, "a" is an ally


def test_a_unit_in_a_siege_tower_stays_hidden():
    g = bare(enemies={E1: "MILITIA"})
    fog.update(g, {"v": at(10, 10), E1: at(60, 10)})
    g.towers = {"t": [E1]}
    assert fog.update(g, {"v": at(60, 11), E1: at(60, 10)}) == []
    assert E1 in g.fog["hidden"]


def test_tick_once_a_second_and_not_with_reveal_all():
    g = bare()
    g.where = lambda want: {"v": at(10, 10), E1: at(60, 10)} if want >= {"v", E1, E2} else {}
    fog.tick(g)
    assert g.sent == [f"aoe hide @a[team=p1] {E1}"]
    g.fog["hidden"], g.now = set(), 0.5
    fog.tick(g)
    assert len(g.sent) == 1                                         # not before EVERY seconds
    g.now = 1.0
    fog.tick(g)
    assert len(g.sent) == 2
    g.reveal, g.now, g.fog["hidden"] = "all", 5.0, set()
    fog.tick(g)
    assert len(g.sent) == 2


def test_many_uuids_split_into_commands_within_rcon_max():
    import replay
    many = {f"00000000-0000-0000-0000-{i:012d}": "MILITIA" for i in range(100)}
    g = bare(enemies=many)
    out = fog.update(g, {"v": at(10, 10)} | {u: at(80, 80) for u in many})
    assert len(out) > 1 and all(len(c) <= replay.RCON_MAX for c in out)
    assert sum(len(c.split()) - 3 for c in out) == 100


@pytest.mark.mc
def test_an_enemy_shows_when_a_villager_walks_to_it_on_a_server(tmp_path):
    """On Paper: an enemy militia far from the villager is in the `aoe hide` set; the villager walks to it, and the
    next update shows it again."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import time

    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import ai, run
    scn = scenarios.new_scenario(32)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=4.5, y=4.5)
    scn.unit_manager.add_unit(scenarios.PlayerId.TWO, UnitInfo.MILITIA.ID, x=26.5, y=4.5)
    src = str(tmp_path / "f.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    enemy = next(o["uuid"] for o in data["objects"] if o["kind"] == "unit" and o["player"] == 2)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data, tick=0.25).setup()
        game.command(f"data merge entity {enemy} {{NoAI:1b}}")      # it stays where it is
        replies, send = [], g.command
        g.command = lambda c: replies.append((c, send(c))) or replies[-1][1]
        end = time.time() + 30
        while enemy not in g.where({enemy}):                           # the datapack puts it on its team
            assert time.time() < end, "the enemy has no team"
            time.sleep(1)
        gather.fog.tick(g)
        assert g.fog["hidden"] == {enemy}
        assert any(c.startswith("aoe hide @a[team=p1]") and enemy in c and r.startswith("Hidden: 1 entities")
                   for c, r in replies), replies
        v, = g.villagers
        x, _, z = g.where({enemy})[enemy]
        ai.move(g, v, "VILLAGER", g.map.T, x - 6, g.map.y(int(x - 6), int(z)), z)
        end = time.time() + 60
        while enemy in g.fog["hidden"]:
            assert time.time() < end, (g.where({v, enemy}), g.fog)
            g.step()
            gather.fog.tick(g)
            time.sleep(g.tick)
        assert any(c.startswith("aoe show @a[team=p1]") and enemy in c and r.startswith("Shown: 1 entities")
                   for c, r in replies), replies
