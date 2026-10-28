"""train.units_of (#3100): the units of a building's menu, also the unit lines of civs.TRAINS (the Mapuche Settlement)
and the units of the upgrades (the dock after Medium Warships trains the war galley). A ship of the dock keeps the
Shipwright bonus, also after an upgrade. A building without units has no rally point. Fake server."""
from test_dock_train import dock_map
from test_folwark import complete, polish
from test_shipwright import imperial

from game import train


def test_the_mapuche_settlement_trains_its_lines_and_has_a_rally_point():
    server, g = polish("MAPUCHE")
    site = complete(g, "SETTLEMENT", 20, 20)
    cell = (site["footprint"][0] + 1, site["footprint"][2] + 1)            # footprint: x0, x1, z0, z1
    assert {"SPEARMAN", "SKIRMISHER"} <= set(train.units_of(g, "SETTLEMENT"))
    rect = train.open_menu(g, "Steve", cell)
    assert rect is not None and train.order(g, "Steve", rect, train.RALLY[0]) == 0
    assert g.rallying["Steve"] == rect


def test_a_building_without_units_has_no_rally_point():
    server, g = imperial()
    assert train.units_of(g, "UNIVERSITY") == [] and train.units_of(g, "BLACKSMITH") == []


def test_the_war_galley_costs_20_percent_less_wood_with_shipwright():
    server, g = imperial()
    g.techs |= {"SHIPWRIGHT", "MEDIUM_WARSHIPS"}
    assert train.price(g, "WAR_GALLEY", "DOCK")["wood"] == 72
    assert train.shipwright(g, "WAR_GALLEY") and train.shipwright(g, "FIRE_SHIP")
    assert train.shipwright(g, "GALLEY") and not train.shipwright(g, "ARCHER")


def test_a_galleon_after_two_upgrades_is_a_ship_of_the_dock():
    server, g = dock_map()
    g.techs |= {"SHIPWRIGHT", "MEDIUM_WARSHIPS", "HEAVY_WARSHIPS"}
    assert "GALLEON" in train.units_of(g, "DOCK") and train.shipwright(g, "GALLEON")
