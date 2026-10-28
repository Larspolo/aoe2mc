"""game/train.py: an upgrade moves the type tag (aoe2mc.t<ID>) of the live units of the line to the new type (#2977).
The triggers count "Own Objects" by this tag: after Crossbowman, the archer counts as CROSSBOWMAN (ID 24). The tag of a
mounted unit sits on its rider, the horse keeps none (units.make_entity)."""
from test_castle_upgrades import RANGE, research, setup

from game import train


def test_the_type_tag_of_a_live_archer_becomes_the_crossbowman_tag():
    server, g = setup()
    research(g, RANGE, "CROSSBOWMAN_UPGRADE")
    assert g.soldiers["c"] == "CROSSBOWMAN"
    assert "tag c remove aoe2mc.t4" in server.log
    assert "execute as c on passengers run tag @s add aoe2mc.t24" in server.log
    assert "execute as c unless entity @s[nbt={Passengers:[{}]}] run tag @s add aoe2mc.t24" in server.log


def test_the_rider_of_a_cavalry_archer_gets_the_tag_and_the_horse_none():
    assert train.type_tag_commands("h", "CAVALRY_ARCHER", "HEAVY_CAVALRY_ARCHER") == (
        "tag h remove aoe2mc.t39", "execute as h on passengers run tag @s remove aoe2mc.t39",
        "execute as h on passengers run tag @s add aoe2mc.t474",
        "execute as h unless entity @s[nbt={Passengers:[{}]}] run tag @s add aoe2mc.t474")


def test_the_units_of_another_line_keep_their_tags():
    server, g = setup()
    research(g, RANGE, "CROSSBOWMAN_UPGRADE")
    assert not [c for c in server.log if c.startswith(("tag a ", "tag p ", "execute as a ", "execute as p "))
                and "aoe2mc.t" in c]
    assert g.soldiers["a"] == "MAN_AT_ARMS" and g.soldiers["p"] == "SPEARMAN"
