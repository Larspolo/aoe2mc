"""The line of sight of the own buildings in the fog of war of the game program (#1470): a complete site and a
garrisoned building see, a destroyed building (its target is gone) does not."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import fog  # noqa: E402
import gather  # noqa: E402

T = 4
E = "00000000-0000-0000-0000-00000000000e"
TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [40 * T, 40 * T, 44 * T, 44 * T]}
UUID = combat.target_uuid(TC["footprint"])


def bare(objects=(), sites=()):
    g = gather.Gather.__new__(gather.Gather)
    g.player, g.data, g.map, g.paper = 1, {"objects": list(objects)}, types.SimpleNamespace(T=T), True
    g.villagers, g.soldiers, g.sites, g.enemies = {}, {}, list(sites), {E: "MILITIA"}
    g.players, g.bots, g.sent, g.now, g.reveal = {}, [], [], 0.0, "normal"
    g.command, g.clock = g.sent.append, lambda: g.now
    return g


def test_a_destroyed_building_sees_nothing():
    g = bare([TC])
    assert (42, 42) in g.seen_tiles({}, {UUID}) and (42, 42) in g.seen_tiles({})   # None: all buildings stand
    assert g.seen_tiles({}, set()) == set()


def test_a_garrisoned_building_sees():
    g = bare([TC])
    g.garrisons = {UUID: {"v1", "v2"}}                               # the units inside give no own sight (AoE2)
    assert (42, 42 - combat.sight("TOWN_CENTER")) in g.seen_tiles({}, {UUID})


def test_a_foundation_sees_nothing_and_a_complete_site_needs_a_target():
    site = {"name": "HOUSE", "player": 1, "footprint": (10 * T, 12 * T, 70 * T, 72 * T), "progress": 0.5}
    g = bare(sites=[site])
    assert g.seen_tiles({}, set()) == set()                           # no sight before it is complete (#4176)
    site["progress"] = 1.0
    assert g.seen_tiles({}, set()) == set()
    assert (11, 71) in g.seen_tiles({}, {combat.target_uuid([10 * T, 70 * T, 12 * T, 72 * T])})


def test_the_fog_hides_the_enemy_near_a_destroyed_building_with_no_new_command():
    g = bare([TC])
    asked = []
    g.where = lambda want: asked.append(set(want)) or ({UUID: (42 * T, 70.0, 42 * T)} if g.now < 1 else {}) \
        | {E: (43.5 * T, 70.0, 43.5 * T)}
    fog.tick(g)
    assert g.sent == [] and UUID in asked[0]                          # the target is in the same aoe where
    g.now = 1.0
    fog.tick(g)
    assert g.sent == [f"aoe hide @a[team=p1] {E}"]
