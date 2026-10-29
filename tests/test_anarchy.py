"""Unique technology of the Goths (#2685): the castle of the Goths researches Anarchy in the Castle Age. After it the barracks trains the Huskarl in the time of the castle, and
the Elite Huskarl after the upgrade at the castle (civs.TRAINS, the key "after")."""
import json
import re

from test_forging import menus, setup

from game import build, gather, savegame, train

BARRACKS, CASTLE = (17, 3), (12, 4)


def player(civ="GOTHS", ages=2):
    server, g = setup()
    g.stock.update(food=10000, gold=10000)
    g.techs.update(build.AGE_TECHS[:ages])
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_goth_castle_researches_anarchy_and_the_elite_upgrade():
    server, g = player()
    assert {"HUSKARL", "ANARCHY"} <= set(train.trains(g, "CASTLE"))
    assert "ELITE_HUSKARL_UPGRADE" in train.trains(g, "CASTLE")
    server, g = player(ages=1)
    assert not train.unlocked(g, "ANARCHY") and train.unlocked(player()[1], "ANARCHY")   # the Castle Age


def test_the_goth_barracks_trains_the_huskarl_only_after_anarchy():
    server, g = player()
    assert "HUSKARL" not in train.trains(g, "BARRACKS")
    train.open_menu(g, "Steve", BARRACKS)
    assert "Huskarl" not in menus(server)[-1]
    g.techs.add("ANARCHY")
    assert "HUSKARL" in train.trains(g, "BARRACKS")
    assert "ELITE_HUSKARL_UPGRADE" not in train.trains(g, "BARRACKS")        # the upgrade stays at the castle
    slot = train.slots("BARRACKS", "HUSKARL")[0]
    train.open_menu(g, "Steve", BARRACKS)
    price = train.price(g, "HUSKARL", "CASTLE")                        # with the Goth infantry discount
    assert price == train.price(g, "HUSKARL", "BARRACKS")
    assert re.search(rf" {slot}:[a-z_]+:Huskarl:{price['food']} food · {price['gold']} gold · ", menus(server)[-1])
    assert "Elite Huskarl" not in menus(server)[-1]
    assert train.queue(g, "Steve", BARRACKS, "HUSKARL")
    assert g.stock["food"] == 10000 - price["food"] and g.stock["gold"] == 10000 - price["gold"]


def test_the_barracks_trains_the_elite_huskarl_after_the_upgrade():
    server, g = player(ages=3)
    g.techs.update({"ANARCHY", "ELITE_HUSKARL_UPGRADE"})
    out = train.trains(g, "BARRACKS")
    assert "ELITE_HUSKARL" in out and "HUSKARL" not in out
    train.open_menu(g, "Steve", BARRACKS)
    p = train.price(g, "ELITE_HUSKARL", "BARRACKS")                    # with the Imperial Age discount
    assert f":Elite Huskarl:{p['food']} food · {p['gold']} gold · " in menus(server)[-1]


def test_a_briton_player_has_no_anarchy_and_no_huskarl_at_the_barracks():
    server, g = player("BRITONS", ages=3)
    g.techs.add("ANARCHY")                                             # also when the research were there
    assert "ANARCHY" not in train.trains(g, "CASTLE") and "HUSKARL" not in train.trains(g, "BARRACKS")


def test_a_save_keeps_the_research():
    server, g = player()
    g.techs.add("ANARCHY")
    h = gather.Gather(server, g.data).setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g))))
    assert "ANARCHY" in h.techs and "HUSKARL" in train.trains(h, "BARRACKS")
