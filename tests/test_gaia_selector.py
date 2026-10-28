"""A trigger effect of Gaia (player 0) finds all Gaia units in its area (#2916): each Gaia unit has the tag aoe2mc.p0
(units.make_entity), also one with a ref tag, one that "Change Ownership" gave to Gaia, and a type filter. The selector
does not match the condition markers aoe2mc.m<ref> and the mounts."""
import numpy as np

import aoe2mc
import units
from test_trigger_ownership import lines


def tags(o):
    """The tags of the unit o, then the tags of its mounts (the other entities of its NBT)."""
    nbt = units.make_entity(dict(rotation=0.0, **o), {}, (0.5, 0.0, 0.5), np.random.default_rng(1))
    stack, found, top = [nbt], [], units.top_entity(nbt)
    while stack:
        e = stack.pop()
        stack += list(e.get("Passengers", []))
        found += [] if e is top else [{str(t) for t in e.get("Tags", [])}]
    return [{str(t) for t in top.get("Tags", [])}, *found]


def matches(sel, tagset):
    """True when the tag parts of the selector sel match an entity with the tags tagset (no player type)."""
    parts = [p for p in sel[3:-1].split(",") if p.startswith("tag=")]
    return all((t[5:] not in tagset) if t.startswith("tag=!") else (t[4:] in tagset) for t in parts)


def effect(player=0, obj=None):
    return dict(type=aoe2mc.FREEZE_OBJECT, player=player, object=obj, area=[2, 3, 4, 5])


def test_the_selector_matches_each_kind_of_gaia_unit():
    sel = aoe2mc.unit_selector(effect(), 4)
    assert "tag=aoe2mc.p0" in sel and "x=8," in sel
    assert matches(sel, tags(dict(name="SHEEP", player=0, id=594))[0])
    assert matches(sel, tags(dict(name="SHEEP", player=0, id=594, ref=7, ref_tag=True))[0])     # a ref tag
    given = {"aoe2mc.t38", "aoe2mc.r9"}                       # "Change Ownership" to Gaia: the old tags and p0
    gaia = [line for line in lines(target=0) if " add aoe2mc.p0" in line]
    assert gaia and matches(sel, given | {"aoe2mc.p0"})
    typed = aoe2mc.unit_selector(effect(obj=594), 4)        # a type filter
    assert matches(typed, tags(dict(name="SHEEP", player=0, id=594))[0])
    assert not matches(typed, tags(dict(name="DEER", player=0, id=65))[0])


def test_the_selector_does_not_match_markers_mounts_or_players():
    sel = aoe2mc.unit_selector(effect(), 4)
    assert not matches(sel, {"aoe2mc.m7"}) and not matches(sel, set())
    assert not matches(sel, {"aoe2mc.p0", units.MOUNT})
    assert not matches(sel, tags(dict(name="KNIGHT", player=1, id=38))[0])


def test_a_gaia_mount_has_the_gaia_tag_and_the_mount_tag():
    for o in (dict(name="KNIGHT", player=0, id=38), dict(name="KNIGHT", player=2, id=38)):
        unit, *mounts = tags(o)
        p = f"aoe2mc.p{o['player']}"
        assert p in unit and mounts and all(m == {p, units.MOUNT} for m in mounts)


def test_a_gaia_source_gives_its_units_to_a_player():
    sel = aoe2mc.unit_selector(effect(), 4)
    assert lines(player=0, target=1) == [f"tag {sel} add aoe_order5_0",
                                        "execute as @e[tag=aoe_order5_0] on vehicle run tag @s add aoe_order5_0",
                                        "execute as @e[tag=aoe_order5_0] on vehicle on passengers run tag @s remove aoe_order5_0",
                                        'data modify storage aoe2mc:orders list append value "owner aoe_order5_0 0 1"',
                                        f"tag {sel} add aoe2mc.own",
                                         "execute as @e[tag=aoe2mc.own] on vehicle run tag @s add aoe2mc.own",
                                         "tag @e[tag=aoe2mc.own] remove aoe2mc.p0", "tag @e[tag=aoe2mc.own] add aoe2mc.p1",
                                         "team join p1 @e[tag=aoe2mc.own]", "tag @e[tag=aoe2mc.own] remove aoe2mc.own"]
