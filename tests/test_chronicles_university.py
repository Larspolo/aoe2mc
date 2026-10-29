"""The naval technologies of the university (#2136, AoE2 DE wiki, The Last Chieftains): Clinker Construction (Castle
Age) and Carvel Hull (Imperial Age, after it) make the ships faster; Siphons (Castle Age) and Incendiaries (Imperial
Age, after it). The wiki availability charts give the civilizations without them (civs.MISSING). Fake server."""
import pytest
from test_castle_upgrades import entry
from test_shipwright import imperial
from test_train_archery import menus

from game import civs, fleet, train


@pytest.mark.parametrize("name", ["CARVEL_HULL", "CLINKER_CONSTRUCTION", "INCENDIARIES", "SIPHONS"])
def test_a_civilization_with_it_sees_it_one_without_it_does_not(name):
    before = train.BY_KEY["after"].get(name)
    techs = (before,) if before else ()
    has = next(r["name"] for r in civs.ROWS if r["name"] not in civs.MISSING.get(name, ())
               and r["name"] not in civs.MISSING.get(before, ()))
    assert train.unlocked(imperial(has, techs=techs)[1], name)
    if civs.MISSING.get(name):
        assert not train.unlocked(imperial(sorted(civs.MISSING[name])[0], techs=techs)[1], name)


def test_the_university_menu_has_them_in_their_age():
    server, g = imperial("KOREANS")                                    # the Italians pay 25 % less
    g.techs -= {"IMPERIAL_AGE"}
    train.open_menu(g, "Steve", (8, 18))
    menu = menus(server)[-1]
    assert entry(g, (8, 18), "CLINKER_CONSTRUCTION") in menu and entry(g, (8, 18), "SIPHONS") in menu
    assert "Carvel Hull" not in menu and "Incendiaries" not in menu
    g.techs |= {"IMPERIAL_AGE", "CLINKER_CONSTRUCTION", "SIPHONS"}
    train.open_menu(g, "Steve", (8, 18))
    menu = menus(server)[-1]
    assert entry(g, (8, 18), "CARVEL_HULL") in menu and entry(g, (8, 18), "INCENDIARIES") in menu


def test_each_one_makes_the_live_and_the_new_ships_faster():
    server, g = imperial()
    g.soldiers["boat"] = "GALLEY"                                      # a live ship
    g.stock.update(food=300, wood=200)
    before = {n: fleet.speed(n, g.map.T, g) for n in ("GALLEY", "TRANSPORT_SHIP", "TRADE_COG", "FISHING_SHIP")}
    rect = train.open_menu(g, "Steve", (8, 18))
    slot = train.layout(g, rect)["CLINKER_CONSTRUCTION"][0]
    assert train.order(g, "Steve", rect, slot) == 1
    server.log.clear()
    train.tick(g, train.seconds(g, "CLINKER_CONSTRUCTION") + 0.1)
    assert "CLINKER_CONSTRUCTION" in g.techs
    assert not any(c.startswith("attribute boat ") for c in server.log)   # a boat: fleet.tick reads the speed
    once = {n: fleet.speed(n, g.map.T, g) for n in before}
    assert all(once[n] > v for n, v in before.items()), once
    assert train.speed(g, "MILITIA") == train.speed(g, "VILLAGER_MALE") == 1
    rect = train.open_menu(g, "Steve", (8, 18))
    assert train.layout(g, rect)["CARVEL_HULL"][0] == slot                # now Carvel Hull in the same slot
    assert train.order(g, "Steve", rect, slot) == 1
    train.tick(g, train.seconds(g, "CARVEL_HULL") + 0.1)
    assert "CARVEL_HULL" in g.techs and fleet.speed("GALLEY", g.map.T, g) > once["GALLEY"]
