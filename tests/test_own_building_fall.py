"""game/ruins.py: an own building whose target entity falls leaves the lists of its owner at the next check: its menu,
its queue (with the cost back), its population room, its count for the age rules, its garrison, the trade routes and
the conquest (#3008)."""
import json
import re

import pytest
from test_bot_train import with_buildings
from test_trade_cart import setup as markets_map
from test_trade_cog import docks_map
from test_train_population import setup as town

from game import combat, conquest, fleet, gather, ruins, savegame, trade, train

TC, HOUSE = (2, 5, 2, 5), (9, 11, 14, 16)                          # block footprints (x0, x1, z0, z1) of town()
ROOM = train.HOUSING["TOWN_CENTER"], train.HOUSING["HOUSE"]          # the population room of each


def uuid(rect):
    x0, x1, z0, z1 = rect
    return combat.target_uuid([x0, z0, x1, z1])


def stand(server, rects, player=1):
    """The server answers `aoe where` of the building targets, and `execute if entity` of a target or of the targets
    of a team, as the plugin: the targets of the footprints rects stand. Returns the live {UUID: player}: a test takes
    a target out of it (0 hit points) or puts one in (a new building)."""
    live, command = {uuid(r): player for r in rects}, server.command

    def answer(cmd):
        if m := re.fullmatch(r"aoe where @e\[tag=aoe2mc\.building,team=p(\d+),tag=!aoe2mc\.wall\] (\d+)", cmd):
            server.log.append(cmd)
            found = sorted(u for u, p in live.items() if p == int(m[1]))
            page = found[int(m[2]):int(m[2]) + gather.WHERE_PAGE]
            return f"Where {len(found)}: " + ", ".join(f"{u} 0.00 64.00 0.00 0 0" for u in page)
        if m := re.fullmatch(r"execute if entity @e\[tag=aoe2mc\.building,team=p(\d+),tag=!aoe2mc\.wall\]", cmd):
            server.log.append(cmd)
            return "Test passed" if int(m[1]) in live.values() else "Test failed"
        if (m := re.fullmatch(r"execute if entity (\S{36})", cmd)) and m[1] in live:
            server.log.append(cmd)
            return "Test passed"
        return command(cmd)
    server.command = answer
    return live


def check(g):
    """The next check of ruins.tick, with no wait."""
    g.ruins_at = 0.0
    ruins.tick(g)


def fallen_town(houses=1):
    server, g = town(houses=houses)
    g.paper = True
    return server, g, stand(server, [TC] + [(9 + 2 * i, 11 + 2 * i, 14, 16) for i in range(houses)])


def test_a_fallen_town_center_opens_no_menu_and_trains_nothing():
    server, g, live = fallen_town()
    cost = train.price(g, "VILLAGER_MALE")["food"]
    for _ in range(2):
        train.queue(g, "Steve", (3, 3))
    assert len(g.queues[TC]) == 2 and g.stock["food"] == 1000 - 2 * cost
    check(g)
    del live[uuid(TC)]                                                 # the plugin removed the target: 0 hit points
    check(g)
    assert TC not in train.homes(g) and train.open_menu(g, "Steve", (3, 3)) is None
    assert not g.queues.get(TC) and g.stock["food"] == 1000            # the cost of the queue comes back
    assert f"scoreboard players add Food aoe_res {cost}" in server.log
    for _ in range(200):
        g.step()
    assert train.tick(g, 60) == [] and not [c for c in server.log if c.startswith("summon")]


def test_a_bot_does_not_train_at_its_fallen_town_center():
    server, me, b = with_buildings("HOUSE", "HOUSE", "HOUSE")
    b.g.paper = True
    live = stand(server, [(20, 23, 20, 23)], player=2)
    b.g.stock["food"] = 1000
    check(b.g)
    del live[uuid((20, 23, 20, 23))]
    check(b.g)
    b.recruit()
    assert not any(b.g.queues.values()) and b.g.stock["food"] == 1000


def test_a_fallen_house_takes_its_room_and_a_fallen_mill_its_age_count():
    server, g, live = fallen_town()
    g.data["objects"] += [{"kind": "building", "name": "BARRACKS", "player": 1, "footprint": [14, 2, 17, 5]},
                          {"kind": "building", "name": "MILL", "player": 1, "footprint": [14, 8, 16, 10]}]
    live |= {uuid((14, 17, 2, 5)): 1, uuid((14, 16, 8, 10)): 1}
    check(g)
    assert train.limit(g) == sum(ROOM) and train.missing(g, "FEUDAL_AGE") is None
    del live[uuid(HOUSE)], live[uuid((14, 16, 8, 10))]
    check(g)
    assert train.limit(g) == ROOM[0] and train.owned(g) == ["TOWN_CENTER", "BARRACKS"]
    assert train.missing(g, "FEUDAL_AGE").endswith("(1/2)")


def test_the_units_inside_a_fallen_built_building_come_out():
    server, g, live = fallen_town()
    rect = (14, 17, 8, 11)
    site = {"name": "TOWN_CENTER", "player": 1, "footprint": list(rect), "progress": 1.0, "done": True}
    g.sites.append(site)
    live[uuid(rect)] = 1
    g.garrisons[rect] = ["v"]
    g.villagers["v"].state = "garrison"
    check(g)
    assert rect in train.homes(g) and g.garrisons[rect] == ["v"]
    del live[uuid(rect)]
    check(g)
    assert site not in g.sites and rect not in g.garrisons and g.villagers["v"].state == "idle"
    assert "tag v remove aoe2mc.garrisoned" in server.log


def test_a_fallen_market_ends_the_route_of_a_trade_cart():
    server, g = markets_map()
    far = (18, 21, 16, 19)
    live = stand(server, [(2, 5, 2, 5), far])
    g.selected = {"c"}
    assert trade.order(g, "Steve", (19, 17)) == far and "c" in g.trade
    check(g)
    del live[uuid(far)]
    check(g)
    trade.tick(g)
    assert "c" not in g.trade and trade.markets(g) == [(2, 5, 2, 5)]


def test_a_trade_cog_with_a_fallen_dock_stops_at_its_next_stop_with_no_gold():
    server, g = docks_map()
    far = (14, 17, 32, 35)
    train.order(g, "Steve", train.open_menu(g, "Steve", (15, 3)), train.MORE)
    cog, = train.tick(g, train.seconds(g, "TRADE_COG", "DOCK"))
    g.selected = {cog}
    assert fleet.trade_order(g, "Steve", (15, 33)) == far
    ruins.fall(g, far)                                                 # the check found its target gone
    for _ in range(200):
        fleet.tick(g, 0.5)
    assert g.ships[cog].state == "idle" and g.stock["gold"] == 0


def test_a_player_whose_last_building_a_built_house_fell_is_defeated():
    server, g = town(houses=0)
    g.paper = True
    rect = (14, 16, 8, 10)
    live = stand(server, [rect])
    g.data["objects"] = [o for o in g.data["objects"] if o["player"] != 1]   # no unit and no start building
    g.sites = [{"name": "HOUSE", "player": 1, "footprint": list(rect), "progress": 1.0, "done": True}]
    check(g)
    assert conquest.alive(g, 1)
    del live[uuid(rect)]
    assert not conquest.alive(g, 1)                                     # the target counts, not the complete site
    check(g)
    assert not g.sites
    g.sites = [{"name": "HOUSE", "player": 1, "footprint": list(rect), "progress": 0.5}]
    assert conquest.alive(g, 1)                                         # a foundation counts, as in AoE2


def test_a_building_with_no_target_never_falls():
    server, g = town(houses=1)
    g.paper = True
    stand(server, [])                                                   # no target was ever there
    for _ in range(3):
        check(g)
    assert TC in train.homes(g) and train.limit(g) == sum(ROOM) and not g.ruins


def test_a_new_building_on_the_footprint_of_a_fallen_one_works_as_a_home():
    server, g, live = fallen_town()
    check(g)
    del live[uuid(TC)]
    check(g)
    assert g.ruins == {TC} and TC not in train.homes(g)
    g.sites.append({"name": "TOWN_CENTER", "player": 1, "footprint": list(TC), "progress": 1.0, "done": True})
    check(g)                                                            # its target comes with build.target
    live[uuid(TC)] = 1
    check(g)
    assert train.homes(g)[TC] == "TOWN_CENTER" and train.open_menu(g, "Steve", (3, 3)) == TC
    del live[uuid(TC)]
    check(g)
    assert not g.sites and TC not in train.homes(g)                     # it falls too


@pytest.mark.parametrize("name", ["TOWN_CENTER", "HOUSE"])
def test_a_save_keeps_the_fallen_start_buildings(name):
    server, g, live = fallen_town()
    rect = {"TOWN_CENTER": TC, "HOUSE": HOUSE}[name]
    check(g)
    del live[uuid(rect)]
    check(g)
    _, h = town()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g))))
    assert h.ruins == {rect} and name not in train.owned(h) and rect not in train.homes(h)


@pytest.mark.mc
def test_a_destroyed_house_leaves_the_own_buildings_on_a_server(tmp_path):
    """Paper: after `aoe destroy` of the target of an own house, the next check takes the house out of train.owned."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io

    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    from game import run
    scn = scenarios.new_scenario(24)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=6, y=6)
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.HOUSE.ID, x=16, y=6)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=6.5, y=13.5)
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
        check(g)
        assert sorted(train.owned(g)) == ["HOUSE", "TOWN_CENTER"] and train.limit(g) == sum(ROOM)
        game.command(f"aoe destroy {combat.target_uuid(house['footprint'])}")
        check(g)
        assert train.owned(g) == ["TOWN_CENTER"] and train.limit(g) == ROOM[0] and g.ruins == {(x0, x1, z0, z1)}
