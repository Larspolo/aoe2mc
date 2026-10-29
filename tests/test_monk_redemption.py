"""Redemption (#1264): the monastery researches it (Castle Age, AoE2 wiki "Redemption"), and then a
monk converts siege units and the enemy buildings that are not LASTING (AoE2 wiki "Conversion"): next to a building,
from the 15th to the 25th interval."""
from test_monk_convert import setup, until_converted
from test_monk_techs import learn
from test_monk_train import monastery

from game import combat, garrison, gather, monk, train

HOUSE = {"kind": "building", "name": "BARRACKS", "player": 2, "footprint": [20, 4, 23, 7]}


def test_the_monastery_researches_redemption():
    assert train.HELP["REDEMPTION"]
    server, g = monastery()
    rect = learn(g, "REDEMPTION")
    assert g.queues[rect][0]["name"] == "REDEMPTION"
    train.tick(g, train.seconds(g, "REDEMPTION", "MONASTERY"))
    assert "REDEMPTION" in g.techs


def fort(*others, building=HOUSE):
    """setup() with the enemy building of the entry `building`: its target entity stands in its middle."""
    server, g = setup(*others)
    g.data["objects"].append(dict(building))
    g.forts, g.fort_names = {}, {}
    uuid = combat.target_uuid(building["footprint"])
    g.forts[uuid] = (20, 64, 4, 22, 70, 6)
    g.fort_names[uuid] = building["name"]
    server.entities[uuid] = {"Pos": (21.5, 64.0, 5.5)}
    return server, g, uuid


def test_without_redemption_no_building_and_no_siege():
    server, g, uuid = fort(("ram", "BATTERING_RAM", 2, 8.5))
    assert not monk.convert_order(g, {"monk"}, uuid) and not monk.convert_order(g, {"monk"}, "ram")


def test_with_redemption_a_monk_converts_a_ram_next_to_it():
    server, g = setup(("ram", "BATTERING_RAM", 2, 8.5), ("mango", "MANGONEL", 2, 12.5))
    g.techs.add("REDEMPTION")
    assert monk.convert_order(g, {"monk"}, "ram")
    monk.convert(g, 0.25)
    assert any(c.startswith("aoe moveto monk") for c in server.log), "3 blocks away: it walks next to the ram"
    server.entities["monk"]["Pos"] = (6.5, 64.0, 5.5)
    assert until_converted(g, "ram") <= 9 * monk.INTERVAL and "ram" in g.soldiers
    g.faith.clear()
    assert monk.convert_order(g, {"monk"}, "mango")                    # a mangonel: from 9 tiles
    assert until_converted(g, "mango") <= 9 * monk.INTERVAL


def test_with_redemption_a_monk_converts_a_building_in_15_to_25_intervals():
    times = []
    for seed in range(20):
        server, g, uuid = fort()
        g.techs.add("REDEMPTION")
        g.chance.seed(seed)
        assert monk.convert_order(g, {"monk"}, uuid)
        monk.convert(g, 0.25)
        assert "aoe moveto monk 19.5 64 5.5" in server.log, "to the side of the building next to the monk"
        server.entities["monk"]["Pos"] = (19.0, 64.0, 5.5)
        t = 0.0
        while uuid in g.forts and t < 40:
            monk.convert(g, 0.25)
            t += 0.25
        times.append(t)
        assert f"team join p1 {uuid}" in server.log and g.data["objects"][-1]["player"] == 1
        assert "A monk converts the Barracks." in " ".join(server.log)
    assert min(times) >= 15 * monk.INTERVAL and max(times) <= 25.25 * monk.INTERVAL and len(set(times)) > 2


def test_a_converted_building_works_for_its_new_player():
    server, g, uuid = fort(building={"kind": "building", "name": "WATCH_TOWER", "player": 2,
                                     "footprint": [20, 4, 23, 7]})
    g.techs.add("REDEMPTION")
    server.entities["monk"]["Pos"] = (19.0, 64.0, 5.5)
    monk.convert_order(g, {"monk"}, uuid)
    monk.convert(g, 40.0)
    assert uuid not in g.forts and (20, 23, 4, 7) in garrison.holders(g)


def test_no_monk_converts_a_town_center_castle_wall_or_wonder():
    for name in ("TOWN_CENTER", "CASTLE", "STONE_WALL", "GATE_AA1", "WONDER", "MONASTERY", "FARM", "FISH_TRAP"):
        server, g, uuid = fort(building=HOUSE | {"name": name})
        g.techs.add("REDEMPTION")
        assert not monk.convert_order(g, {"monk"}, uuid), name


def test_a_right_click_with_a_monk_on_an_enemy_building_converts_it():
    server, g, uuid = fort()
    g.techs.add("REDEMPTION")
    g.soldiers["monk"] = "MONK"
    g.choose({"monk"}, "monk")
    g.target = lambda *a: ("fort", uuid, set())
    g.look = lambda name: ((0, 70, 0), (1, 0, 0))
    gather.Gather.click(g, "Steve")
    assert g.converting["monk"][0] == uuid and uuid in g.sieged
