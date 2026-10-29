"""Fire Lancer (#1953): the barracks of a civilization with it trains the fire lancer from the Castle Age and researches
Elite Fire Lancer in the Imperial Age. The upgrade turns the live fire lancers into elite ones, and the barracks then
trains the elite one."""
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

from game import civs, combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
WITHOUT = sorted(civs.MISSING["FIRE_LANCER"])[:2]


def entry(g, name, state, icon=None):
    """The menu item of name with its cost and time for the player of g."""
    slot, item, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {k}" for k, v in train.COSTS[name].items())
    return f"{slot}:{icon or item}:{label}:{cost} · {train.seconds(g, name):g} s · {state}"


def barracks(civ="JURCHENS", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["fl"] = "FIRE_LANCER"
    g.game.entities.setdefault("fl", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_barracks_menu_has_the_fire_lancer_from_the_castle_age_for_a_civ_with_it():
    server, g = barracks(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", BARRACKS)
    assert entry(g, "FIRE_LANCER", "Needs the Castle Age", "gray_dye") in menus(server)[-1]
    server, g = barracks("CHINESE", CASTLE)
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert f" {entry(g, 'FIRE_LANCER', 'queue 0/15')} " in menu
    assert "Elite Fire Lancer" not in menu                             # the upgrade: the Imperial Age
    for civ in WITHOUT:
        server, g = barracks(civ, CASTLE)
        train.open_menu(g, "Steve", BARRACKS)
        assert "Fire Lancer" not in menus(server)[-1]
        assert train.queue(g, "Steve", BARRACKS, "FIRE_LANCER") is None


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = barracks()
    train.open_menu(g, "Steve", BARRACKS)
    up = "ELITE_FIRE_LANCER_UPGRADE"
    assert f" {entry(g, up, 'research')} " in menus(server)[-1] + " "
    research(g, BARRACKS, up)
    assert g.soldiers["fl"] == "ELITE_FIRE_LANCER"
    assert combat.stats_command("fl", "ELITE_FIRE_LANCER", train.stats(g, "ELITE_FIRE_LANCER"), civs.taken(g, "ELITE_FIRE_LANCER"),
                                civs.friendly(g, "ELITE_FIRE_LANCER")) in server.log   # with the civilization factors (#2418)
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert f" {entry(g, 'ELITE_FIRE_LANCER', 'queue 0/15')} " in menu
    assert ":Fire Lancer:" not in menu and f"{train.ITEMS[up][0]}:book" not in menu
    assert train.queue(g, "Steve", BARRACKS, "ELITE_FIRE_LANCER") and train.queue(g, "Steve", BARRACKS, "FIRE_LANCER") is None


def test_gambesons_adds_its_pierce_armor():
    server, g = barracks()
    old = {n: train.stats(g, n) for n in ("FIRE_LANCER", "ELITE_FIRE_LANCER")}
    research(g, BARRACKS, "GAMBESONS")
    for n in old:
        assert train.stats(g, n) == old[n]._replace(pierce=train.stats(g, n).pierce) and train.stats(g, n).pierce > old[n].pierce
