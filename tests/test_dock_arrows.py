"""game/garrison.py: fishing ships go into an own dock, and the dock shoots one arrow for each of them, at most its
garrison size, as in AoE2 DE (#1949). Fake server, no Minecraft."""
import re

from test_dock_train import DOCK, dock_map, trained
from test_train_menu import menus

from game import combat, fleet, garrison, gather, train


def test_the_dock_shoots_one_arrow_for_each_fishing_ship_inside():
    most = garrison.SIZES["DOCK"]
    assert garrison.arrows("DOCK", []) == 0                            # an empty dock does not shoot
    assert garrison.arrows("DOCK", ["FISHING_SHIP"] * 2) == min(2, most)
    assert garrison.arrows("DOCK", ["FISHING_SHIP"] * (most + 2)) == most   # at most one arrow per garrison place
    assert garrison.arrows("DOCK", ["FISHING_SHIP", "GALLEY"]) == 1    # a galley adds no arrow


def test_the_dock_target_has_its_attack_line():
    uuid = combat.target_uuid([14, 11, 17, 14])
    cmds = combat.building(uuid, "DOCK", 1, (14, 63, 11, 16, 71, 13), T=4)
    assert f"aoe arrows {uuid} 0" in cmds                              # no arrow before a fishing ship is inside
    line, = [c for c in cmds if c.startswith("aoe building ")]
    s, low = combat.stats("DOCK"), combat.FORT_MIN_RANGE.get("DOCK", 0)
    assert line.split()[3:6] == [str(s.hp), str(s.melee), str(s.pierce)]   # hit points, melee and pierce armor
    reload = str(round(s.reload / gather.NORMAL * 20))
    assert line.split()[12:16] == [str(s.attack), str(s.range * 4), reload, str(low * 4)]   # attack, range, reload, min range
    assert line.split()[-1].split(",") == [f"{c}:{n}" for c, n in sorted(s.bonus.items())]   # the bonus vs. ships


def paper_dock(wood=200):
    server, g = dock_map(wood)
    g.paper = True
    plain = server.command

    def command(cmd):                                                  # the target entity of the dock is there
        if re.fullmatch(r"execute if entity \S+", cmd):
            server.log.append(cmd)
            return "Test passed"
        return plain(cmd)
    server.command = command
    return server, g


def test_a_fishing_ship_goes_into_the_dock_and_comes_out_with_ungarrison():
    server, g = paper_dock()
    uuid = trained(server, g)
    assert fleet.order(g, {uuid}, (21, 3))
    for _ in range(40):
        fleet.tick(g, 1.0)
    g.select(uuid)
    assert garrison.order(g, "Steve", (15, 12)) == DOCK and g.entering == {uuid: DOCK}
    assert not any(c.startswith("aoe moveto") for c in server.log)    # a boat has no Minecraft path finding
    for _ in range(40):
        fleet.tick(g, 1.0)
        garrison.tick(g)
    assert g.garrisons[DOCK] == [uuid] and not g.entering and uuid not in g.selected
    assert uuid in garrison.inside(g)
    tp = next(c for c in server.log if c.startswith(f"tp {uuid} "))
    x, z = (float(v) for v in tp.split()[2::2])
    assert DOCK[0] <= x < DOCK[1] and DOCK[2] <= z < DOCK[3]          # gone from the water: in the dock
    assert f"execute as {uuid} on passengers run data merge entity @s {garrison.CREW}" in server.log
    assert f"aoe arrows {combat.target_uuid([14, 11, 17, 14])} 1" in server.log
    for _ in range(5):                                                 # it stays inside: no fishing, no sailing
        fleet.tick(g, 1.0)
        garrison.tick(g)
    assert g.garrisons[DOCK] == [uuid]

    train.open_menu(g, "Steve", (15, 12))
    slot, icon, label = garrison.ungarrison("DOCK")[:3]
    assert f"{slot}:{icon}:{label}" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, slot) == 0 and DOCK not in g.garrisons   # the menu item: all come out
    tp = [c for c in server.log if c.startswith(f"tp {uuid} ")][-1].split()
    cell = (int(float(tp[2])), int(float(tp[4])))
    assert g.map.wet(*cell) and cell in fleet.pier(g, DOCK)          # back on the water next to the dock
    assert g.ships[uuid].cell == cell and g.ships[uuid].state == "idle"
    assert f"aoe arrows {combat.target_uuid([14, 11, 17, 14])} 0" in server.log


def test_a_land_unit_does_not_go_into_the_dock():
    server, g = paper_dock()
    trained(server, g)
    g.villagers["v0"] = gather.Villager("v0", (12.5, 64.0, 12.5))
    server.entities["v0"] = {"Pos": (12.5, 64.0, 12.5)}
    g.select("v0")
    assert garrison.order(g, "Steve", (15, 12)) is None and not g.entering   # the click opens the dock menu


def test_a_click_on_the_dock_on_the_water_sends_the_selected_fishing_ship_in():
    server, g = paper_dock()
    uuid = trained(server, g)
    g.select(uuid)
    g.click("Steve")                                                   # Steve looks east and down at the dock
    assert g.entering == {uuid: DOCK}


def test_no_menu_item_of_a_garrison_building_is_in_its_ungarrison_slot():
    for building in garrison.SIZES:
        slots = {train.ITEMS[n][0] for n in train.TRAINS.get(building, ())}
        assert garrison.ungarrison(building)[0] not in slots, building
