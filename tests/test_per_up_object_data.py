"""The data of a found object in AI scripts (#4959): up-get-object-data, up-object-data, up-get-object-target-data,
up-object-target-data, up-remove-objects, up-get-object-type-data, up-get-upgrade-id, up-store-object-name. The map of
test_per_up_search: the bot (player 2) has the soldiers m1 (MILITIA), m2 (SPEARMAN) and k1 (KNIGHT)."""
from test_per_up_search import run, script

from game import combat, per


def target(s, b, monkeypatch, hp=33.4, at=(9.5, 4.0, 13.5)):
    monkeypatch.setattr(type(b), "hp", lambda self, t: hp)
    monkeypatch.setattr(type(b.g), "positions", lambda self, us: {u: at for u in us})
    run(s, "(up-find-local c: militiaman-line c: 5) (up-set-target-object search-local c: 0)")
    return s.target


def test_the_data_of_the_target_object_its_type_and_its_upgrade(monkeypatch, capsys):
    s, b, me = script()
    oid = target(s, b, monkeypatch)
    T = b.g.map.T
    s.rules = per.parse(f"""
(defrule (true) => (up-get-object-data object-data-hitpoints 1) (up-get-object-data object-data-point-x 2)
                   (up-get-object-data object-data-point-y 3) (up-get-object-data 20 4) (up-get-object-data object-data-id 5)
                   (up-get-object-data object-data-heresy 6) (up-get-object-target-data object-data-id 7)
                   (up-get-object-type-data c: militia object-data-maxhp 8) (set-goal 9 74)
                   (up-get-upgrade-id my-player-number 0 9 10) (up-store-object-name) (disable-self))
(defrule (up-object-data object-data-player == {b.g.player}) (up-object-data object-data-hitpoints == 34)
         (not (up-object-target-data object-data-id >= 0)) => (set-goal 11 1))
""")
    s.step()
    assert [s.goals.get(i) for i in range(1, 6)] == [34, int(9.5 // T), int(13.5 // T), b.g.player, oid]
    assert s.goals[6] == -1 and s.goals[7] == -1 and s.goals[11] == 1                  # no value: -1
    assert s.goals[8] == combat.stats("MILITIA").hp and s.goals[10] == 74 and s.text == "militia"
    err = capsys.readouterr().err
    assert err.count("unknown object data object-data-heresy") == 1 and err.count("unknown object target") == 1


def test_remove_objects_by_data_and_by_index(monkeypatch):
    s, b, me = script()
    target(s, b, monkeypatch)
    run(s, "(up-find-local c: infantry-class c: 20)")
    found = list(s.search[1]["found"])
    run(s, f"(up-remove-objects search-local object-data-id == {found[0]})")
    assert s.search[1]["found"] == [i for i in found if i != found[0]]
    run(s, "(up-remove-objects search-local object-data-index >= 1)")
    assert s.search[1]["found"] == [i for i in found if i != found[0]][:1]
