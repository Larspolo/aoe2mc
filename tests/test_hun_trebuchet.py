"""A Hun trebuchet hits units more often (#2479, epic #1088; AoE2 DE wiki "Trebuchet"): the key "accuracy" of
game/data/units.jsonl and of the Huns line of game/data/civs.jsonl, combat.accuracy_command and `aoe accuracy` of the
plugin. Fake server, and a trebuchet on a server."""
import contextlib
import io
import json
import time

import pytest
from test_armenian_volley import summoned

from game import combat, gather, run


def accuracy(log, uuid):
    """The accuracy of the `aoe accuracy` command of uuid in log."""
    a, = [float(c.split()[-1]) for c in log if c.startswith(f"aoe accuracy {uuid} ")]
    return a


def test_a_hun_trebuchet_hits_units_more_often():
    uuid, log = summoned("HUNS", "TREBUCHET")
    hun = accuracy(log, uuid)
    uuid, log = summoned("BRITONS", "TREBUCHET")
    assert 0 < accuracy(log, uuid) < hun < 1


def test_other_units_hit_each_time():
    uuid, log = summoned("HUNS", "MANGONEL")
    assert not any(c.startswith("aoe accuracy") for c in log)
    assert combat.accuracy_command("u", "TREBUCHET", 0.9) is None      # 100 %: no command


def test_a_trebuchet_of_the_map_gets_the_accuracy_of_its_civ():
    sent = []
    game = type("G", (), {"command": lambda self, c: sent.append(c) or ""})()
    data = {"objects": [{"kind": "unit", "name": "TREBUCHET", "player": 1, "uuid": "t1"},
                        {"kind": "unit", "name": "TREBUCHET", "player": 2, "uuid": "t2"}],
            "players": {"1": {"civ": "HUNS"}, "2": {"civ": "FRANKS"}}, "tile_size": 4}
    combat.setup(game, data)
    assert accuracy(sent, "t1") > accuracy(sent, "t2") > 0              # the Huns hit more often


@pytest.mark.mc
def test_a_trebuchet_with_accuracy_0_misses_and_with_1_hits_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo
    scn = scenarios.new_scenario(32)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.TREBUCHET.ID, x=6.5, y=16.5)
    um.add_unit(scenarios.PlayerId.TWO, UnitInfo.SPEARMAN.ID, x=16.5, y=16.5)   # 10 tiles: in the range of 16
    src = str(tmp_path / "t.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        t, = [u for u, n in g.soldiers.items() if n == "TREBUCHET"]
        foe, = [o["uuid"] for o in data["objects"] if o.get("name") == "SPEARMAN"]
        assert "Accuracy: 1 units" in game.command(f"aoe accuracy {t} 0")

        def alive():
            return "passed" in game.command(f"execute if entity {foe}")
        g.choose({t}, t)
        g.attack(foe)
        end = time.time() + 30                                         # the unpack and 3 shots or more
        while time.time() < end:
            g.step()
            time.sleep(g.tick)
        assert alive()                                                 # each shot missed
        game.command(f"aoe accuracy {t} 1")
        end = time.time() + 20
        while alive() and time.time() < end:
            g.step()
            time.sleep(g.tick)
        assert not alive()                                             # 200 attack: one hit kills it
