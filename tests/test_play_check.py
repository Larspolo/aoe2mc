"""tools/play_check.py: the driver of player 1 and the stuck units of a scripted game against the bot (#3324)."""
from test_bot_gather import bot_map

import play_check
from game import gather


def driver():
    server, me, b = bot_map()
    return server, me, b, play_check.Driver(me, b.g)


def test_the_driver_gives_orders_and_does_not_step_the_gather():
    server, me, b, d = driver()
    steps = []
    me.step = lambda: steps.append(1)
    d.step()
    assert steps == []                                                 # Gather.run steps it
    assert getattr(me, "share", None) is None                          # conquest: player 1 stays a person
    assert d.share is b.g and d.foe == 2


def ready(me, villagers=20):
    """Player 1 with the two buildings of the Feudal Age and this many villagers."""
    me.sites += [{"name": n, "player": 1, "done": True, "footprint": [8, 9, 8, 9]} for n in ("LUMBER_CAMP", "MILL")]
    me.villagers.update({f"v{i}": gather.Villager(f"v{i}", (6.5, 64.0, 6.5)) for i in range(villagers - 1)})


def test_the_driver_saves_for_the_feudal_age_and_researches_it():
    server, me, b, d = driver()
    ready(me)
    me.stock.update(food=100, wood=0, gold=0, stone=0)
    d.advance()
    assert d.saving == "FEUDAL_AGE"
    d.recruit()
    assert not any(me.queues.values())                                 # no villager: the food goes to the age
    me.stock["food"] = 500
    d.advance()
    assert [e["name"] for q in me.queues.values() for e in q] == ["FEUDAL_AGE"] and me.stock["food"] == 0


def test_without_the_buildings_or_the_villagers_of_the_age_the_driver_trains_villagers():
    for villagers in (1, 19):                                          # no buildings; the buildings and 19 villagers
        server, me, b, d = driver()
        if villagers > 1:
            ready(me, villagers)
        me.stock.update(food=500)
        d.advance()
        assert d.saving is None
        d.recruit()
        assert [e["name"] for q in me.queues.values() for e in q] == ["VILLAGER_MALE", "VILLAGER_MALE"]


def test_a_soldier_that_stands_far_from_its_target_is_stuck():
    server, me, b, d = driver()
    me.soldiers["s1"] = "MILITIA"
    server.entities["s1"] = {"Pos": (6.5, 64.0, 10.5)}
    d.targets["s1"] = "b0"                                             # a villager of the bot at (24.5, 19.5)
    w = play_check.Watch(me, [d])
    for now in (0, 30, 59):
        w.sample(d, now)
    assert w.stuck == {}
    w.sample(d, 61)
    assert w.stuck["s1"]["unit"] == "MILITIA" and w.stuck["s1"]["seconds"] == 61


def test_a_soldier_that_fights_or_walks_is_not_stuck():
    server, me, b, d = driver()
    me.soldiers.update(s1="MILITIA", s2="MILITIA")
    server.entities["s1"] = {"Pos": (24.5, 64.0, 21.0)}               # next to its target b0
    server.entities["s2"] = {"Pos": (6.5, 64.0, 10.5)}
    d.targets.update(s1="b0", s2="b1")
    w = play_check.Watch(me, [d])
    for now in range(0, 125, 5):
        server.entities["s2"]["Pos"] = (6.5 + now / 10, 64.0, 10.5)   # it walks
        w.sample(d, now)
    assert w.stuck == {}


def test_a_villager_that_walks_nowhere_is_stuck():
    server, me, b, d = driver()
    v = me.villagers["p1"]
    v.state, v.goal = "to_tree", (26, 21)
    w = play_check.Watch(me, [d])
    for now in (0, 30, 65):
        w.sample(d, now)
    assert w.stuck["p1"]["order"] == "to_tree (26, 21)"
    v.state = "chop"                                                   # it works: no order to walk
    w.stuck.clear()
    w.sample(d, 130)
    assert w.stuck == {}


def test_the_errors_of_the_server_log(tmp_path):
    log = tmp_path / "latest.log"
    log.write_text("[12:00:00 INFO]: Done (3.1s)!\n[12:00:01 ERROR]: Could not pass event\n"
                   "java.lang.NullPointerException: x\n[12:00:02 ERROR]: Could not pass event\n")
    assert play_check.errors(str(log)) == ["[12:00:01 ERROR]: Could not pass event", "java.lang.NullPointerException: x"]
    assert play_check.errors(str(tmp_path / "none.log")) == []


def test_the_town_bell_rings_while_foe_soldiers_are_near(monkeypatch):
    server, me, b, d = driver()
    calls = []
    monkeypatch.setattr(play_check.garrison, "holders", lambda g: {(2, 6, 2, 6): {"name": "TOWN_CENTER"}})
    monkeypatch.setattr(play_check.garrison, "order", lambda g, who, cell: calls.append(("in", sorted(g.selected), cell)) or (2, 6, 2, 6))
    monkeypatch.setattr(play_check.garrison, "out", lambda g, rect: calls.append(("out", rect)))
    d.foes = {"b0": (5.5, 64.0, 5.5)}
    d.bell()
    d.bell()                                                           # rung: no second order
    assert calls == [("in", ["p1"], (2, 2))] and d.rung == (2, 6, 2, 6)
    t, d.looked, me.stock["food"] = d.time, d.time, 500                # no new look in this step
    d.orders()                                                         # the villagers wait: no work, the time goes on
    assert d.time > t and not any(me.queues.values()) and d.rung
    d.foes = {}
    d.bell()
    assert calls[-1] == ("out", (2, 6, 2, 6)) and d.rung is None


def test_a_transport_ship_does_not_defend():
    server, me, b, d = driver()
    me.soldiers.update(t1="TRANSPORT_SHIP", m1="MILITIA")
    server.entities["t1"] = {"Pos": (6.5, 64.0, 9.5)}
    server.entities["m1"] = {"Pos": (6.5, 64.0, 10.5)}
    b.g.soldiers["e1"] = "MILITIA"
    server.entities["e1"] = {"Pos": (8.5, 64.0, 8.5)}
    d.defend()
    assert d.targets == {"m1": "e1"}
