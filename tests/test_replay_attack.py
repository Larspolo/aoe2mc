"""Live replay on Paper: an ORDER on an enemy unit or building sends the military units of the selection to attack it,
with the AoE2 values of game/combat.py (#632). Fake RCON, and one fight on a Paper server."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import ai  # noqa: E402
import combat  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_ai import MIL, orders, play  # noqa: E402
from test_replay_spawn import queue, summons  # noqa: E402
from test_replay_walk import HOUSE, VIL  # noqa: E402

ENEMY = dict(MIL, name="ARCHER", player=2, uuid="e1", ref=20, tile=[12.5, 10.5])
CASTLE = dict(HOUSE, name="CASTLE", player=2, ref=21, tile=[12.0, 4.0], footprint=[40, 8, 56, 24])


def attacks(sent):
    return [c for c in sent if c.startswith("aoe attack ")]


def test_an_order_on_an_enemy_unit_attacks_with_the_military_units():
    r, sent, _ = play([dict(time=0, player=1, kind="order", objects=[7, 8], target=20)], (VIL, MIL, HOUSE, ENEMY))
    assert attacks(sent) == ["aoe attack u2 e1"]                     # the militia attacks
    assert ai.speed_command("u2", "MILITIA", 4, 4.0) in sent
    assert set(orders(sent)) == {"u1"} and 8 not in r.moving          # the villager walks to it


def test_an_order_on_an_enemy_building_attacks_its_target():
    _, sent, _ = play([dict(time=0, player=1, kind="order", objects=[8], target=21)], (MIL, HOUSE, CASTLE))
    assert attacks(sent) == [f"aoe attack u2 {combat.target_uuid([40, 8, 56, 24])}"]


def test_an_order_on_an_own_unit_or_building_or_the_ground_is_a_walk():
    own = dict(ENEMY, player=1)
    for e in (dict(time=0, player=1, kind="order", objects=[8], target=20),
              dict(time=0, player=1, kind="order", objects=[8], target=9),
              dict(time=0, player=1, kind="move", objects=[8], tile=[10.5, 10.5])):
        _, sent, _ = play([e], (MIL, HOUSE, own))
        assert not attacks(sent) and set(orders(sent)) == {"u2"}


def test_without_the_plugin_there_is_no_attack():
    d = data([dict(time=0, player=1, kind="order", objects=[8], target=20)])
    d["objects"] += [MIL, HOUSE, ENEMY]
    game = replay.Replay(Fake(), d)
    assert game.commands(d["timeline"][0]) == [] and not attacks(game.game.sent)


def test_a_spawned_unit_gets_its_aoe2_values_on_paper():
    d = data([queue(name="ARCHER", type=4, objects=(9,))])
    d["objects"] += [HOUSE]
    for ai_on in (True, False):
        r = replay.Replay(Fake(), d, ai=ai_on)
        e, = r.spawns()
        cmds = r.commands(e)
        uuid = r.new[0][1].uuid
        assert len(summons(cmds)) == 1
        assert (combat.stats_command(uuid, "ARCHER") in cmds) == ai_on
        assert (combat.range_command(uuid, "ARCHER", 4) in cmds) == ai_on


@pytest.mark.mc
def test_two_replay_units_fight_and_one_dies(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import time

    import run
    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=6.5, y=8.5)
    scn.unit_manager.add_unit(scenarios.PlayerId.TWO, UnitInfo.VILLAGER_MALE.ID, x=9.5, y=8.5)
    src = str(tmp_path / "fight.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data_ = json.load(f)
    units_ = [o for o in data_["objects"] if o["kind"] == "unit"]
    for k, o in enumerate(units_):                                     # the object IDs of a record
        o["ref"] = 100 + k
    militia, = [o for o in units_ if o["player"] == 1]
    villager, = [o for o in units_ if o["player"] == 2]
    data_["timeline"] = [dict(time=0, player=1, kind="order", objects=[militia["ref"]], target=villager["ref"])]
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data_)
        r = replay.Replay(game, data_, ai=True)
        r.run(1.0, log=None)
        end = time.time() + 60
        while "No entity was found" not in game.command(f"data get entity {villager['uuid']} Health"):
            assert time.time() < end, "the villager lives after 60 s"
            time.sleep(1)
        assert "has the following entity data" in game.command(f"data get entity {militia['uuid']} Health")
