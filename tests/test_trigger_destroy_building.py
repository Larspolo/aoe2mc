"""#2910 (epic #2538): a trigger with the condition "Destroy Object" on a building fires in the scenario mode when the
building falls. The converter tests the score #f<ref> of aoe_fallen; the game program sets it once when the target
entity of the building is gone (game/scenario.py fallen). A unit keeps the tag test (test_trigger_destroy.py)."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import combat  # noqa: E402
import gather  # noqa: E402
import scenario  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402

import aoe2mc  # noqa: E402

BUILDING = {"kind": "building", "name": "CASTLE", "player": 2, "ref": 7, "footprint": [4, 4, 8, 8]}
UUID = combat.target_uuid(BUILDING["footprint"])


def destroy(ref=7, inverted=False):
    return dict(type=aoe2mc.DESTROY_OBJECT, timer=0, inverted=inverted, ref=ref, unit=False)


def trig(conds):
    return dict(id=5, name="t", enabled=True, looping=False, conditions=conds,
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Fallen!", player=1, time=0, object=None,
                              tile=[-1, -1], area=[-1] * 4)])


def tick(conds):
    return aoe2mc.trigger_files([trig(conds)])[1]["data/aoe2mc/function/tick.mcfunction"].splitlines()


class Standing(FakeServer):
    """A server where the target entities listed in alive stand; the other target entities are gone."""

    def __init__(self, alive):
        super().__init__({})
        self.alive = alive

    def command(self, cmd):
        if m := re.fullmatch(r"execute if entity (\S+)", cmd):
            self.log.append(cmd)
            return "Test passed, count: 1" if m[1] in self.alive else "Test failed"
        return super().command(cmd)


def test_the_condition_tests_the_score_of_the_building_in_the_tick_function():
    assert tick([destroy()]) == ["execute if score #f7 aoe_fallen matches 1.. unless score #5 aoe_trig matches 1 "
                                 "run function aoe2mc:trigger/5"]


def test_an_inverted_condition_holds_while_the_building_stands():
    assert "execute unless score #f7 aoe_fallen matches 1.. unless score #5 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/5" in tick([destroy(inverted=True)])


def test_a_tick_function_lists_the_refs_of_the_buildings_for_the_game_program():
    triggers = [trig([destroy(ref=7)]), trig([destroy(ref=3)])]
    assert aoe2mc.fallen_list(triggers) == [3, 7]
    assert "scoreboard objectives add aoe_fallen dummy" in aoe2mc.trigger_files(triggers)[0]


def test_the_scenario_mode_sets_the_score_once_when_the_building_falls():
    server = Standing({UUID})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], [BUILDING])).setup()
    g.data["fallen"] = [7]
    scenario.fallen(g)
    assert not [c for c in server.log if "aoe_fallen" in c]          # it stands: no score
    server.alive.clear()                                              # the building falls
    g.fallen_at = 0.0
    scenario.fallen(g)
    scenario.fallen(g)
    assert [c for c in server.log if "aoe_fallen" in c] == ["scoreboard players set #f7 aoe_fallen 1"]   # once
