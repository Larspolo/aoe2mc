"""game/stance.py: the formations Line, Box, Staggered and Flank in the third row of the stance menu (#3416). A click
sets the formation of each selected military unit (g.formations); Gather.walk_to uses the most common one of the group."""
import json

from test_formation_line import setup

from game import gather, savegame, stance


def units():
    archers = {f"a{k}": ("ARCHER", 14 + k, 23) for k in range(4)}
    militia = {f"m{k}": ("MILITIA", 14 + k, 25) for k in range(4)}
    return archers, militia


def test_the_menu_has_the_four_formations_in_slots_18_to_21():
    server, g = setup({"m0": ("MILITIA", 14, 25)})
    got = {slot: (name, text) for slot, _, name, text in stance.items(g, "m0")}
    assert [got[s][0] for s in range(18, 22)] == ["Line", "Box", "Staggered", "Flank"]
    assert got[18][1].endswith("Now") and not got[19][1].endswith("Now")


def test_a_click_on_box_sets_the_military_units_and_the_box_holds_the_archers():
    archers, militia = units()
    server, g = setup(archers | militia | {"v0": ("VILLAGER_MALE", 20, 25)})
    g.choose(set(archers) | set(militia) | {"v0"}, "m0")
    stance.open_menu(g, "Steve", "m0")
    g.menus["Steve"]("Steve", 19, False)                               # the player clicks "Box"
    assert g.formations == dict.fromkeys(sorted(archers | militia), "Box")
    assert stance.items(g, "m0")[-3][3].endswith("Now")
    g.choose(set(archers) | set(militia), "m0")
    out = g.walk_to("Steve", (15, 13))
    cx, cz = (sum(c[k] for c in out.values()) / len(out) for k in (0, 1))
    far = {u: abs(out[u][0] - cx) + abs(out[u][1] - cz) for u in out}
    assert min(far, key=far.get) in archers                            # an archer in the middle of the box
    assert sum(far[u] for u in archers) < sum(far[u] for u in militia)  # the ranged units inside, the melee around


def test_line_removes_the_entry_and_a_save_keeps_the_formations():
    archers, militia = units()
    server, g = setup(archers | militia)
    g.choose(set(militia), "m0")
    stance.form(g, "Steve", "Flank")
    g.choose({"m0"}, "m0")
    stance.form(g, "Steve", "Line")
    assert g.formations == {"m1": "Flank", "m2": "Flank", "m3": "Flank"}
    server2, h = setup(archers | militia)
    savegame.load(h, json.loads(json.dumps(savegame.dump(g))))
    assert h.formations == g.formations and isinstance(h, gather.Gather)
