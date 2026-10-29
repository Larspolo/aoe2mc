"""Unique technologies (#2021): the castle of the own civilization researches them in their age (the keys "civ" and
"age" of data/train.jsonl): Chieftains and Bogsveigar of the Vikings."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)
TECHS = ("CHIEFTAINS", "BOGSVEIGAR")


def item(g, name):
    """The menu text of the technology name: slot, item, name, cost, time and state."""
    slot, kind, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {r}" for r, v in train.price(g, name).items())
    return f" {slot}:{kind}:{label}:{cost} · {round(train.seconds(g, name), 1):g} s · research "


def test_only_the_castle_of_the_own_civ_researches_them_in_their_age():
    for name in TECHS:
        civ, age, label = train.BY_KEY["civ"][name], train.BY_KEY["age"].get(name, 0), train.ITEMS[name][2]
        server, g = setup(civ, ages=age)
        train.open_menu(g, "Steve", CASTLE)
        assert item(g, name) in menus(server)[-1] + " "
        if age:
            server, g = setup(civ, ages=age - 1)                       # one age earlier: not yet
            train.open_menu(g, "Steve", CASTLE)
            assert f":{label}:" not in menus(server)[-1]
        other = "BRITONS" if civ != "BRITONS" else "FRANKS"
        server, g = setup(other, ages=3)
        train.open_menu(g, "Steve", CASTLE)
        assert f":{label}:" not in menus(server)[-1]


def test_the_effects_change_the_live_and_the_new_units():
    server, g = setup("VIKINGS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["bk"] = "BERSERK"
    g.game.entities.setdefault("bk", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    before = train.stats(g, "BERSERK")
    assert train.queue(g, "Steve", CASTLE, "CHIEFTAINS")
    train.tick(g, train.seconds(g, "CHIEFTAINS"))
    assert "CHIEFTAINS" in g.techs
    after = train.stats(g, "BERSERK")
    assert after.bonus["cavalry"] > before.bonus.get("cavalry", 0) and after.bonus["camel"] > before.bonus.get("camel", 0)
    assert train.stats(g, "ARBALESTER").bonus == combat.stats("ARBALESTER").bonus   # not infantry
    assert combat.stats_command("bk", "BERSERK", after) in server.log      # the live berserk
    arb = train.stats(g, "ARBALESTER").attack
    assert train.queue(g, "Steve", CASTLE, "BOGSVEIGAR")
    train.tick(g, train.seconds(g, "BOGSVEIGAR"))
    assert train.stats(g, "ARBALESTER").attack > arb and train.stats(g, "BERSERK").attack == after.attack
