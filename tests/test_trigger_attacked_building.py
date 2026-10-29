"""#3775 (epic #3774): a trigger with the condition "Object Attacked" on a building fires in the scenario mode when the
building loses hit points. The converter tests the score #h<ref> of aoe_hit; the game program sets it once per
change of the hit points (game/scenario.py attacked). A unit keeps the tag test (test_trigger_attacked.py)."""
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import aoe2mc  # noqa: E402
import combat  # noqa: E402
import gather  # noqa: E402
import scenario  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402

BUILDING = {"kind": "building", "name": "CASTLE", "player": 2, "ref": 7, "footprint": [4, 4, 8, 8]}
UUID = combat.target_uuid(BUILDING["footprint"])


def attacked(ref=7, inverted=False):
    return dict(type=aoe2mc.OBJECT_ATTACKED, timer=0, inverted=inverted, ref=ref, unit=False)


def trig(conds):
    return dict(id=5, name="t", enabled=True, looping=False, conditions=conds,
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Attacked!", player=1, time=0, object=None,
                              tile=[-1, -1], area=[-1] * 4)])


def tick(conds):
    return aoe2mc.trigger_files([trig(conds)])[1]["data/aoe2mc/function/tick.mcfunction"].splitlines()


class Hurt(FakeServer):
    """A server where the building has the hit points hp (the score aoe_hp of its target entity)."""

    def __init__(self, hp):
        super().__init__({})
        self.hp = hp

    def command(self, cmd):
        if re.fullmatch(r"scoreboard players get \S+ aoe_hp", cmd):
            self.log.append(cmd)
            return f"{UUID} has {self.hp} [] "
        return super().command(cmd)


def test_the_condition_tests_the_score_of_the_building_in_the_tick_function():
    assert "execute if score #h7 aoe_hit matches 1 unless score #5 aoe_trig matches 1 run function aoe2mc:trigger/5" \
        in tick([attacked()])


def test_an_inverted_condition_holds_while_the_building_is_not_hit():
    assert "execute unless score #h7 aoe_hit matches 1 unless score #5 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/5" in tick([attacked(inverted=True)])


def test_a_tick_function_lists_the_refs_of_the_buildings_for_the_game_program():
    triggers = [trig([attacked(ref=7)]), trig([attacked(ref=3)])]
    assert aoe2mc.attacked_list(triggers) == [3, 7]
    assert "scoreboard objectives add aoe_hit dummy" in aoe2mc.trigger_files(triggers)[0]


def test_the_score_is_one_after_the_hit_points_fall_and_zero_at_the_next_read():
    server = Hurt(100)
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], [BUILDING])).setup()
    g.data["attacked"] = [7]
    scenario.attacked(g)
    assert not [c for c in server.log if "aoe_hit" in c]             # full hit points: no score yet
    server.hp = 90                                                    # the building is hit
    g.attacked_at = 0.0
    scenario.attacked(g)
    assert [c for c in server.log if "aoe_hit" in c] == ["scoreboard players set #h7 aoe_hit 1"]
    g.attacked_at = 0.0
    scenario.attacked(g)                                              # the next read, same hit points: back to zero
    assert [c for c in server.log if "aoe_hit" in c] == ["scoreboard players set #h7 aoe_hit 1",
                                                        "scoreboard players set #h7 aoe_hit 0"]
