"""The trigger effect "Create Garrisoned Object" makes units inside the selected buildings (#2764), and UNGARRISON of
the game program lets them out."""
import contextlib
import io
import re
from collections import Counter

from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from test_garrison_game import TC, Server, setup

import aoe2mc
import buildings
from game import garrison
from tools import scenarios

FN = "data/aoe2mc/function/trigger/0.mcfunction"


def test_scenario_effect_summons_garrisoned_archers_in_the_castle(tmp_path):
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(tmp_path / "tiny.aoe2scenario")))
    castle = scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.CASTLE.ID, x=8, y=8)
    t = scn.trigger_manager.add_trigger("Start")
    t.new_condition.timer(timer=5)
    for _ in range(2):
        t.new_effect.create_garrisoned_object(source_player=1, object_list_unit_id_2=UnitInfo.ARCHER.ID,
                                              selected_object_ids=[castle.reference_id])
    path = scenarios.save(scn, str(tmp_path / "a.aoe2scenario"))
    trig, = aoe2mc.read_scenario(path)[4]["triggers"]
    assert trig["effects"][0]["object2"] == ("U", "ARCHER")
    assert trig["effects"][0]["selected"] == [castle.reference_id]
    buildings.INSIDE[castle.reference_id] = ([(33, 34), (34, 34)], 70, (34, 34))
    stats = Counter()
    try:
        _, files = aoe2mc.trigger_files([trig], stats=stats)
    finally:
        del buildings.INSIDE[castle.reference_id]
    summons = [s for s in files[FN].splitlines() if s.startswith("summon ")]
    assert len(summons) == 2 and stats["create garrisoned"] == 2
    for s in summons:
        assert s.split()[2:5] == ["33.5", "70", "34.5"]                # an inside cell of the castle
        assert "Invulnerable: 1b" in s and "NoAI: 1b" in s
        assert aoe2mc.GARRISONED in s and aoe2mc.MADE_INSIDE in s and "aoe2mc.p1" in s


def test_a_holder_with_no_rooms_is_not_supported():
    stats = Counter()
    e = dict(type=aoe2mc.CREATE_GARRISONED_OBJECT, player=1, object2=("U", "ARCHER"), selected=[987654])
    c = aoe2mc.Effect(dict(id=0), 4, None, {}, stats, True, {}, [])
    assert aoe2mc.garrisoned_lines(e, c) == [] and stats["create garrisoned (not supported yet)"] == 1


class Made(Server):
    """`aoe where` finds one archer that a trigger made inside the town center."""
    def command(self, cmd):
        if m := re.fullmatch(r"aoe where (\S+) (\d+)", cmd):
            self.log.append(cmd)
            made = aoe2mc.MADE_INSIDE in m[1] and "a1" not in self.adopted
            return "Where 1: a1 3.5 65.0 3.5" if made else "Where 0: "
        if cmd == f"tag a1 remove {aoe2mc.MADE_INSIDE}":
            self.adopted.add("a1")
        return super().command(cmd)


def test_a_unit_that_a_trigger_made_comes_out_with_ungarrison():
    server, g = setup(villagers=0)
    server.__class__, server.adopted = Made, set()
    garrison.tick(g)
    garrison.tick(g)
    assert g.garrisons[TC] == ["a1"]                                    # once, the tag went
    assert garrison.out(g, TC) == ["a1"]
    assert f"tag a1 remove {aoe2mc.GARRISONED}" in server.log
