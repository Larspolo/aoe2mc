"""game/demolish.py: the item Delete in the menu of an own building or construction site (#3452). A complete building
falls as at 0 hit points (`aoe destroy`, ruins.fall); an unfinished site goes at once with the AoE2 refund."""
import pytest
from menu_line import item
from test_own_building_fall import HOUSE, TC, fallen_town, uuid

from game import demolish, garrison, train


SKY = 260                                                          # air: above each building box


def last_menu(server):
    return [c for c in server.log if c.startswith("aoe menu ")][-1]


def test_the_town_center_menu_has_delete_and_a_click_makes_it_fall():
    server, g, live = fallen_town()
    food = g.stock["food"]
    for _ in range(2):
        train.queue(g, "Steve", (3, 3))
    assert g.stock["food"] < food
    train.open_menu(g, "Steve", (3, 3))
    assert item(last_menu(server), "Delete").startswith(f"{demolish.ITEM[0]}:tnt:")
    train.order(g, "Steve", TC, demolish.ITEM[0])
    assert f"aoe destroy {uuid(TC)}" in server.log
    assert TC not in train.homes(g) and TC in g.ruins
    assert not g.queues.get(TC) and g.stock["food"] == food            # the queue gives its cost back
    assert "aoe menu-close Steve" in server.log


def test_a_house_opens_a_menu_with_only_delete():
    server, g, live = fallen_town()
    assert demolish.open_menu(g, "Steve", (9, 14)) == HOUSE
    assert item(last_menu(server), "Delete") and item(last_menu(server), "Ungarrison") is None
    g.menus["Steve"]("Steve", demolish.ITEM[0], False)
    assert f"aoe destroy {uuid(HOUSE)}" in server.log and HOUSE in g.ruins
    assert all((x, z) not in g.map.blocked for x in range(9, 11) for z in range(14, 16))
    assert demolish.open_menu(g, "Steve", (9, 14)) is None             # it fell: no menu


def test_the_units_inside_come_out():
    server, g, live = fallen_town()
    g.garrisons[TC] = ["v"]
    demolish.delete(g, "Steve", TC)
    assert not g.garrisons.get(TC)


def test_no_delete_for_a_building_of_another_player():
    server, g, live = fallen_town()
    assert demolish.at(g, (19, 19)) is None and demolish.open_menu(g, "Steve", (19, 19)) is None
    assert not demolish.delete(g, "Steve", (19, 21, 19, 21))


def test_vanilla_shows_no_delete_for_a_complete_building():
    server, g, live = fallen_town()
    g.paper = False
    train.open_menu(g, "Steve", (3, 3))
    assert item(last_menu(server), "Delete") is None


def site(g, progress):
    """A house site of player 1 that cost 25 wood (build.found keeps the cost in "paid")."""
    s = {"name": "HOUSE", "player": 1, "footprint": (14, 16, 8, 10), "progress": progress, "paid": {"wood": 25}}
    g.stock["wood"] -= 25
    g.sites.append(s)
    g.map.blocked |= {(x, z) for x in range(14, 16) for z in range(8, 10)}
    return s


def test_an_unstarted_site_gives_its_full_cost_back():
    server, g, live = fallen_town()
    wood = g.stock["wood"]
    s = site(g, 0.0)
    assert g.stock["wood"] == wood - 25
    assert demolish.open_menu(g, "Steve", (15, 9)) == (14, 16, 8, 10)
    g.menus["Steve"]("Steve", demolish.ITEM[0], False)
    assert s not in g.sites and g.stock["wood"] == wood
    assert all((x, z) not in g.map.blocked for x in range(14, 16) for z in range(8, 10))
    assert any(c.startswith("fill 14 ") and c.endswith("minecraft:air") for c in server.log)


def test_a_started_site_gives_nothing_back():
    server, g, live = fallen_town()
    wood = g.stock["wood"]
    s = site(g, 0.3)
    g.villagers["v"].state, g.villagers["v"].site = "build", s
    demolish.delete(g, "Steve", (14, 16, 8, 10))
    assert s not in g.sites and g.stock["wood"] == wood - 25
    assert g.villagers["v"].site is None and g.villagers["v"].state == "idle"


def test_the_menu_of_a_tower_with_units_inside_has_delete():
    server, g, live = fallen_town()
    g.data["objects"].append({"kind": "building", "name": "WATCH_TOWER", "player": 1, "footprint": [14, 8, 16, 10]})
    live[uuid((14, 16, 8, 10))] = 1
    g.garrisons[(14, 16, 8, 10)] = ["v"]
    assert garrison.open_menu(g, "Steve", (15, 9)) == (14, 16, 8, 10)
    assert item(last_menu(server), "Delete") and item(last_menu(server), "Ungarrison")
    g.menus["Steve"]("Steve", demolish.ITEM[0], False)
    assert (14, 16, 8, 10) in g.ruins and not g.garrisons.get((14, 16, 8, 10))


@pytest.mark.mc
def test_a_deleted_house_leaves_its_footprint_free_of_blocks_on_a_server(tmp_path):
    """Paper: the item Delete of an own house makes it fall: no block of it stays above the ground."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json

    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo

    from game import combat, gather, run
    scn = scenarios.new_scenario(24)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.HOUSE.ID, x=16, y=6)
    src = str(tmp_path / "g.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    house = next(o for o in data["objects"] if o["name"] == "HOUSE")
    x0, z0, x1, z1 = house["footprint"]
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25).setup()
        assert g.paper
        _, y0, _, _, y1, _ = combat.building_box(house, g.map.ground)
        box = f"{x0} {y0 + 1} {z0} {x1 - 1} {y1} {z1 - 1}"

        def empty():                                               # the box is the same as a box of air in the sky
            return "Test passed" in game.command(f"execute if blocks {box} {x0} {SKY} {z0} all")
        assert not empty()                                         # the house stands
        assert demolish.delete(g, "Steve", (x0, x1, z0, z1))
        assert empty() and (x0, x1, z0, z1) in g.ruins
