"""The trigger effect "Change Ownership" with the target player 0 makes the units of the player in the area Gaia units
(#2908): they and their mounts lose the tag aoe2mc.p<old>, get the tag aoe2mc.p0 and leave the team, as a Gaia unit has
the tag aoe2mc.p0 and no team (units.make_entity, #2916)."""
from test_trigger_ownership import lines, trig

import aoe2mc


def test_the_units_of_player_1_in_the_area_go_to_gaia():
    sel = aoe2mc.area_selector(trig(target=0)["effects"][0], 4)
    assert lines(target=0) == [f"tag {sel} add aoe_order5_0",
                              "execute as @e[tag=aoe_order5_0] on vehicle run tag @s add aoe_order5_0",
                              "execute as @e[tag=aoe_order5_0] on vehicle on passengers run tag @s remove aoe_order5_0",
                              'data modify storage aoe2mc:orders list append value "owner aoe_order5_0 1 0"',
                              f"tag {sel} add aoe2mc.own",
                               "execute as @e[tag=aoe2mc.own] on vehicle run tag @s add aoe2mc.own",
                               "tag @e[tag=aoe2mc.own] remove aoe2mc.p1", "tag @e[tag=aoe2mc.own] add aoe2mc.p0",
                               "team leave @e[tag=aoe2mc.own]",
                               "tag @e[tag=aoe2mc.own] remove aoe2mc.own"]   # the temporary tag goes last
    assert not any("team join" in line for line in lines(target=0))

