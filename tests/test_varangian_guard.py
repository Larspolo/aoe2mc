"""Varangian Guard (#2011): the barracks of the own civilizations (game/data/civs.jsonl) trains the Varangian Guard from
the Castle Age and researches Elite Varangian Guard in the Imperial Age, with the values of game/data/train.jsonl. The
upgrade turns the live guards into elite ones. The gold while it attacks is not here: the game program has no gold
income from combat."""
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

from game import civs, combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
UNIT, ELITE, UPGRADE = "VARANGIAN_GUARD", "ELITE_VARANGIAN_GUARD", "ELITE_VARANGIAN_GUARD_UPGRADE"
OWN = sorted({r["name"] for r in civs.ROWS} - set(civs.MISSING[UNIT]))[0]   # a civilization that has it
OTHERS = sorted(civs.MISSING[UNIT])[:2]


def barracks(civ=OWN, ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["vg"] = UNIT
    g.game.entities.setdefault("vg", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def item(g, name, state):
    """The menu text of name: slot, item, name, cost, time and state."""
    slot, kind, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {r}" for r, v in train.price(g, name).items())
    return f" {slot}:{kind}:{label}:{cost} · {round(train.seconds(g, name), 1):g} s · {state} "


def label(name):
    return train.ITEMS[name][2]


def test_a_player_of_an_own_civ_sees_it_at_the_barracks_and_another_player_does_not():
    server, g = barracks(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", BARRACKS)
    assert f":gray_dye:{label(UNIT)}:" in menus(server)[-1] and "Needs the Castle Age" in menus(server)[-1]
    server, g = barracks(OWN, CASTLE)
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert item(g, UNIT, f"queue 0/{train.QUEUE}") in menu
    assert f":{label(UPGRADE)}:" not in menu                          # the upgrade: the Imperial Age
    assert train.queue(g, "Steve", BARRACKS, UNIT)
    for civ in OTHERS:
        server, g = barracks(civ, CASTLE)
        train.open_menu(g, "Steve", BARRACKS)
        assert f":{label(UNIT)}:" not in menus(server)[-1]
        assert train.queue(g, "Steve", BARRACKS, UNIT) is None


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = barracks()
    train.open_menu(g, "Steve", BARRACKS)
    assert item(g, UPGRADE, "research") in menus(server)[-1] + " "
    research(g, BARRACKS, UPGRADE)
    assert g.soldiers["vg"] == ELITE
    assert combat.stats_command("vg", ELITE, train.stats(g, ELITE)) in server.log   # with the civilization bonus
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert item(g, ELITE, f"queue 0/{train.QUEUE}") in menu
    assert f":{label(UNIT)}:" not in menu and f" {train.ITEMS[UPGRADE][0]}:book" not in menu
    assert train.queue(g, "Steve", BARRACKS, ELITE)
    assert train.queue(g, "Steve", BARRACKS, UNIT) is None
