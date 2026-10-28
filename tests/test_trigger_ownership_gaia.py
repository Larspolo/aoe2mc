"""The trigger effect "Change Ownership" with the target player 0 makes the units of the player in the area Gaia units
(#2908): they and their mounts lose the tag aoe2mc.p<old> and leave the team, as a Gaia unit has no player tag and no
team (units.make_entity)."""
import aoe2mc
import triggers
from test_trigger_ownership import lines, trig


def test_the_units_of_player_1_in_the_area_go_to_gaia():
    sel = aoe2mc.area_selector(trig(target=0)["effects"][0], 4)
    assert lines(target=0) == [f"tag {sel} add aoe2mc.own",
                               "execute as @e[tag=aoe2mc.own] on vehicle run tag @s add aoe2mc.own",
                               "tag @e[tag=aoe2mc.own] remove aoe2mc.p1", "team leave @e[tag=aoe2mc.own]",
                               "tag @e[tag=aoe2mc.own] remove aoe2mc.own"]   # the temporary tag goes last
    assert not any("team join" in line or "aoe2mc.p0" in line for line in lines(target=0))


def test_a_gaia_source_writes_no_command():
    assert lines(player=0, target=1) == []


def test_the_row_of_map_names_this_ticket():
    assert "#2908" in triggers.MAP[("effect", "CHANGE_OWNERSHIP")]
