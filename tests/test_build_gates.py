"""game/build.py: a palisade gate or a gate on an own wall line (#1324). Fake server, no Minecraft."""
import math
import types

from test_build_site import site_map

from game import build, combat


def line(g, a, b):
    """A wall line of palisade from block cell a to b (tile size 1)."""
    build.wall(g, "Steve", "PALISADE_WALL", a)
    build.wall(g, "Steve", "PALISADE_WALL", b)


def blocks(site):
    """The (x, z) of each block of the design of a site."""
    return {(x, z) for c in site["commands"] if (b := build.box(c)) and b[1].split("[")[0] not in ("air", "minecraft:air")
            for x in range(b[0][0], b[0][3] + 1) for z in range(b[0][2], b[0][5] + 1)}


def test_the_menu_has_the_gates_with_the_aoe2_values_and_the_age_lock():
    server, g = site_map()
    items = {name: (icon, lore) for _, icon, name, lore in build.items(g)}
    assert items["Palisade Gate"] == ("stripped_spruce_log", "30 wood\n30 s")             # AoE2 DE wiki infobox
    assert items["Gate"] == (build.LOCKED, "30 stone\n70 s\nNeeds the Feudal Age")
    g.techs = {"FEUDAL_AGE"}
    assert dict((n, i) for _, i, n, _ in build.items(g))["Gate"] == "iron_bars"
    assert combat.WALLS["PALISADE_GATE"] == ((240, 400, 400, 400), 2, 4) and combat.WALLS["GATE"][1:] == (6, 6)


def test_a_gate_replaces_the_wall_tiles_under_it_and_takes_its_cost():
    server, g = site_map(wood=200)
    line(g, (6, 10), (11, 10))
    assert g.stock["wood"] == 200 - 6 * 3
    a, b = g.sites[:2]
    build.rise(g, a, math.inf)                                         # a complete tile: its target goes
    site = build.gate(g, "Steve", "PALISADE_GATE", (8, 10))
    assert site["name"] == "PALISADE_GATE" and site["footprint"] == (6, 10, 10, 11)
    assert g.stock["wood"] == 200 - 6 * 3 - 30 and server.chosen == 0               # AoE2: no refund of the walls
    assert [s["footprint"][0] for s in g.sites] == [10, 11, 6]
    assert f"kill {combat.target_uuid([6, 10, 7, 11])}" in server.log
    assert {x for x, z in blocks(site)} == {6, 7, 8, 9} and {z for x, z in blocks(site)} == {10}   # along the wall
    assert not any(g.map.free(x, 10) for x in range(6, 10))           # closed for now


def test_a_gate_follows_a_wall_along_z_and_the_builders_go_on_to_it():
    server, g = site_map(wood=200)
    line(g, (15, 6), (15, 11))
    old = g.sites[3]
    g.villagers = {"u": types.SimpleNamespace(uuid="u", site=old)}
    sent = []
    g.build = lambda site, who: sent.append((site, who))
    site = build.gate(g, "Steve", "PALISADE_GATE", (15, 7))            # the clicked tile is one of the 4
    assert site["footprint"] == (15, 16, 6, 10) and sent == [(site, {"u"})]
    assert {x for x, z in blocks(site)} == {15} and {z for x, z in blocks(site)} == {6, 7, 8, 9}
    assert build.rise(g, site, math.inf)
    assert any(c.startswith(f"aoe building {combat.target_uuid([15, 6, 16, 10])} 240 2 4 ") for c in server.log)


def test_a_gate_off_a_wall_line_is_refused_with_a_chat_line():
    server, g = site_map(wood=200)
    assert build.gate(g, "Steve", "PALISADE_GATE", (8, 10)) is None
    line(g, (6, 10), (8, 10))                                          # 3 tiles: too short
    line(g, (8, 12), (8, 13))                                          # a corner is not a straight line
    assert build.gate(g, "Steve", "PALISADE_GATE", (8, 10)) is None
    assert len(g.sites) == 5 and g.stock["wood"] == 200 - 5 * 3
    assert any("must go on 4 tiles of an own wall in a straight line" in c for c in server.log)


def test_no_gate_without_the_resources_or_the_age():
    server, g = site_map(wood=200)
    line(g, (6, 10), (11, 10))
    g.stock["wood"] = 29
    assert build.gate(g, "Steve", "PALISADE_GATE", (8, 10)) is None and len(g.sites) == 6
    assert any("a palisade gate costs 30 wood" in c for c in server.log)
    eye, d = (8.5, 65.62, 12.5), (1.0, -0.5, 0.0)
    assert build.place(g, "Steve", "GATE", eye, d) is None
    assert any("Gate: Needs the Feudal Age" in c for c in server.log)
