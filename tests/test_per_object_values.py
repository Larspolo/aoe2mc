"""The airef object data with a value in the game program (#5184): the type data, the state of a villager, a soldier
and a building, the place, the technology lines, the target of an object, and up-clean-search by a data. The map of
test_per_up_search: the bot (player 2) has a town center, the villagers b0 to b4 and the soldiers m1, m2 and k1."""
import math

from test_per_up_search import run, script

from game import civs, combat, per, train
from game.replay import SPEEDS


def value(s, key, data):
    s.objects(s.bot.g)
    return s.object_value(s.ids[key], data)


def tc(b):
    o = next(o for o in b.g.data["objects"] if o["name"] == "TOWN_CENTER" and o["player"] == b.g.player)
    x0, z0, x1, z1 = o["footprint"]
    return combat.target_uuid(o["footprint"]), (x0, x1, z0, z1)


def test_the_type_data_of_a_soldier_and_a_building():
    s, b, me = script()
    st = combat.stats("MILITIA")
    assert value(s, "m1", "object-data-class") == per.klass("MILITIA") != -1
    assert value(s, "m1", "object-data-category") == 70 and value(s, tc(b)[0], "object-data-category") == 80
    assert value(s, "m1", "object-data-reload-time") == round(st.reload * 1000)
    assert value(s, "m1", "object-data-speed") == round(SPEEDS["MILITIA"] * civs.speed(b.g, "MILITIA") * 100)
    assert value(s, "m1", "object-data-train-site") == per.TYPE_IDS["BARRACKS"]
    assert value(s, "m1", "object-data-train-time") == round(train.seconds(b.g, "MILITIA"))
    assert value(s, "m1", 2) == value(s, "m1", "object-data-class")                       # by the airef id


def test_the_queue_and_the_garrison_of_a_building():
    s, b, me = script()
    key, rect = tc(b)
    assert [value(s, key, f"object-data-{d}") for d in ("train-count", "researching", "progress-type")] == [0, 0, 0]
    assert value(s, "b0", "object-data-train-count") == -2                               # a villager trains nothing
    b.g.queues[rect] = [{"name": "LOOM", "progress": 0.4, "player": 2}, {"name": "VILLAGER_MALE", "progress": 0.0}]
    assert value(s, key, "object-data-train-count") == 1 and value(s, key, "object-data-researching") == 1
    assert value(s, key, "object-data-progress-type") == 103 and value(s, key, "object-data-progress-value") == 40
    b.g.garrisons = {rect: ["b0", "b1"]}
    assert value(s, key, "object-data-garrison-count") == 2 and value(s, "b2", "object-data-garrison-count") == 0


def test_the_state_of_a_villager_and_of_a_soldier():
    s, b, me = script()
    v = b.g.villagers["b0"]
    v.load, v.res, v.state = 7, "gold", "idle"
    assert value(s, "b0", "object-data-carry") == 7 and value(s, "b0", "object-data-resource") == per.RESOURCE_IDS["gold"]
    assert value(s, "b0", "object-data-idling") == 1 and value(s, "b0", "object-data-action") == -1
    assert value(s, "b0", "object-data-cmdid") == per.FILTER_IDS["cmdid-villager"]["id"]
    v.state = "chop"
    assert value(s, "b0", "object-data-action") == per.FILTER_IDS["actionid-gather"]["id"]
    assert value(s, "b0", "object-data-order") == per.FILTER_IDS["orderid-gather"]["id"]
    assert value(s, "m1", "object-data-idling") == 1 and value(s, "m1", "object-data-target-id") == -1
    b.targets = {"m1": "b3"}
    assert value(s, "m1", "object-data-idling") == 0
    assert value(s, "m1", "object-data-target-id") == s.ids["b3"]
    assert value(s, "m1", "object-data-target") == per.klass("VILLAGER_MALE")


def test_the_target_commands_read_the_data_of_the_target(monkeypatch, capsys):
    s, b, me = script()
    monkeypatch.setattr(type(b), "hp", lambda self, t: 20.0 if t == "b3" else 40.0)
    s.objects(b.g)
    s.target, b.targets = s.ids["m1"], {"m1": "b3"}
    s.rules = per.parse("(defrule (true) => (up-get-object-target-data object-data-hitpoints 1) (disable-self))\n"
                        f"(defrule (up-object-target-data object-data-id == {s.ids['b3']}) => (set-goal 3 1))")
    s.step()
    assert s.goals[1] == 20 and s.goals[3] == 1 and "object target" not in capsys.readouterr().err
    b.targets = {}
    assert not s.check(("up-object-target-data", "object-data-id", ">=", 0))             # no target: -1


def test_the_place_and_the_distance_to_the_target_point():
    s, b, me = script()
    p = b.g.positions(["b0"])["b0"]
    T = b.g.map.T
    assert value(s, "b0", "object-data-precise-x") == int(p[0] / T * 100)
    assert value(s, "b0", "object-data-distance") == -1                                  # no target point
    s.point = (int(p[0] / T) + 3, int(p[2] / T) + 4)
    d = math.dist((p[0] / T, p[2] / T), s.point)
    assert value(s, "b0", "object-data-distance") == int(d)
    assert value(s, "b0", "object-data-precise-distance") == int(d * 100)
    assert value(s, "b0", "object-data-full-distance") == int(d * d)
    assert value(s, "b0", "object-data-on-mainland") == 1
    assert value(s, "b0", "object-data-map-zone-id") == s.map_value("zone", s.position("position-self"))


def test_a_technology_line_counts_for_its_objects_only():
    s, b, me = script()
    rows = [r for r in per.OBJECT_DATA_ROWS.values() if r.get("value") == "tech"]
    assert rows and all(value(s, "b0", r["name"]) == 0 for r in rows)                   # nothing researched
    b.g.techs |= {r["tech"] for r in rows}
    for r in rows:
        assert value(s, "b0", r["name"]) == int(r["who"] in ("all", "units")), r["name"]
        assert value(s, tc(b)[0], r["name"]) == int(r["who"] in ("all", "ranged")), r["name"]


def test_clean_search_sorts_by_a_data(monkeypatch):
    s, b, me = script()
    hp = {"m1": 30.0, "m2": 10.0, "k1": 20.0}
    monkeypatch.setattr(type(b), "hp", lambda self, t: hp.get(t))
    run(s, "(up-find-local c: infantry-class c: 20) (up-find-local c: knight-line c: 20)")
    by = sorted(s.search[1]["found"], key=lambda i: hp[next(k for k, j in s.ids.items() if j == i)])
    run(s, "(up-clean-search search-local object-data-hitpoints search-order-asc)")
    assert s.search[1]["found"] == by
    run(s, "(up-clean-search search-local object-data-hitpoints search-order-desc)")
    assert s.search[1]["found"] == by[::-1]
