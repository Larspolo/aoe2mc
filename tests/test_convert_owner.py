"""A unit that a monk converts leaves all lists of its old owner and goes into the right list of its new owner (#2993,
epic #2991): owners.give. One function (gather.soldier) decides "soldier or villager". Fake server of test_gather."""
import pytest
from test_gather import FakeServer, grid

from game import bot, gather, hill, monk, run, train

MAP = [[64] * 24 for _ in range(24)]
POS = {"monk": (3.5, 64.0, 2.5), "vil": (12.5, 64.0, 12.5), "foe": (13.5, 64.0, 12.5)}


def objects(*more):
    return [{"kind": "unit", "name": "MONK", "player": 1, "uuid": "monk", "tile": [3.5, 2.5]},
            {"kind": "unit", "name": "VILLAGER_MALE", "player": 2, "uuid": "vil", "tile": [12.5, 12.5]},
            {"kind": "unit", "name": "MILITIA", "player": 2, "uuid": "foe", "tile": [13.5, 12.5]}, *more]


def with_bot(*more):
    """Player 1 and a bot of player 2 on one data of aoe2mc.json (run.play)."""
    data = grid(MAP, objects(*more))
    server = FakeServer({u: {"Pos": p} for u, p in POS.items()} | {o["uuid"]: {"Pos": (14.5, 64.0, 14.5)} for o in more})
    g = gather.Gather(server, data).setup()
    b = bot.Bot(server, data, share=g, start={}).setup()
    g.bots = [b]
    return server, g, b


def test_converted_units_leave_the_bot():
    server, g, b = with_bot()
    assert "vil" in b.g.villagers and "foe" in b.g.soldiers
    b.g.selected, b.g.groups[1] = {"foe"}, {"foe", "vil"}
    monk.take(g, "vil")
    monk.take(g, "foe")
    assert "vil" not in b.g.villagers and "foe" not in b.g.soldiers and not b.g.selected and b.g.groups[1] == set()
    assert not [u for u in b.g.units if u.get("uuid") in ("vil", "foe")]
    assert {"vil", "foe"} <= set(b.g.enemies) and not {"vil", "foe"} & set(g.enemies)
    assert "vil" in g.villagers and g.soldiers["foe"] == "MILITIA"
    server.log.clear()
    b.step()
    assert not [c for c in server.log if " vil " in f" {c} " or " foe " in f" {c} "]
    assert hill.units(g)["vil"] == hill.units(g)["foe"] == 1


def test_a_trained_unit_changes_its_owner_record():
    server, g, b = with_bot()
    uuid = train.summon(b.g, "MILITIA", (13.5, 64.0, 15.5))
    server.entities[uuid] = {"Pos": (13.5, 64.0, 15.5)}
    monk.take(g, uuid)
    assert monk.owners.player(g, uuid) == 1 and uuid not in b.g.soldiers and uuid in b.g.enemies


def test_a_person_cannot_select_a_unit_that_another_person_converted():
    server = FakeServer({u: {"Pos": p} for u, p in POS.items()})
    data = grid(MAP, objects())
    g, g2 = gather.Gather(server, data).setup(), gather.Gather(server, data, player=2).setup()
    g.bots = [run.Side(g2)]
    g2.peers = [g]
    g2.select("foe")
    monk.take(g, "foe")
    assert "foe" not in g2.selected and "foe" not in g2.soldiers and g2.enemies["foe"] == "MILITIA"
    assert "foe" not in g2.pickable()
    assert "tag foe remove " + gather.SELECT in server.log


@pytest.mark.parametrize("name", ["TRADE_CART_EMPTY", "TRADE_COG", "FISHING_SHIP", "TRANSPORT_SHIP"])
def test_a_converted_cart_or_ship_is_a_soldier(name):
    server, g, b = with_bot({"kind": "unit", "name": name, "player": 2, "uuid": "x", "tile": [14.5, 14.5]})
    assert b.g.soldiers["x"] == name
    monk.take(g, "x")
    assert g.soldiers["x"] == name and "x" not in g.villagers and not [u for u in g.units if u.get("uuid") == "x"]
    assert "x" not in b.g.soldiers


def test_one_function_decides_soldier_or_villager():
    assert all(map(gather.soldier, ["MILITIA", "MONK", "TRADE_CART_EMPTY", "TRADE_COG", "FISHING_SHIP", "MULE_CART"]))
    assert not any(map(gather.soldier, ["VILLAGER_MALE", "VILLAGER_FEMALE"]))
