"""game/train.py: the archery range researches Cranequins in the Imperial Age (#2161, AoE2 DE wiki "Cranequins",
revision 1081203); the (heavy) mounted crossbowmen get more range and more attack against infantry. Only some
civilizations have it, in place of Parthian Tactics."""
from test_castle_upgrades import RANGE, entry, setup
from test_forging import menus

from game import civs, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
CIVS = {r["name"] for r in civs.ROWS} - set(civs.MISSING["CRANEQUINS"])   # the civilizations with it


def player(civ=min(CIVS), ages=IMPERIAL):
    server, g = setup(ages=ages, techs=())
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    g.soldiers["mc"] = "MOUNTED_CROSSBOWMAN"
    g.game.entities.setdefault("mc", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_help_text_is_short():
    assert len(train.HELP["CRANEQUINS"]) <= 50


def test_only_its_civilizations_have_it_in_place_of_parthian_tactics():
    assert CIVS <= set(civs.MISSING["PARTHIAN_TACTICS"])
    server, g = player()
    train.open_menu(g, "Steve", RANGE)
    assert " " + entry(g, RANGE, "CRANEQUINS") + "research " in menus(server)[-1] + " "
    server, g = player(ages=("FEUDAL_AGE", "CASTLE_AGE"))
    train.open_menu(g, "Steve", RANGE)
    assert "Cranequins" not in menus(server)[-1]
    server, g = player(min(civs.MISSING["CRANEQUINS"]))
    train.open_menu(g, "Steve", RANGE)
    assert "Cranequins" not in menus(server)[-1] and train.queue(g, "Steve", RANGE, "CRANEQUINS") is None


def test_the_mounted_crossbowmen_get_range_and_attack_against_infantry():
    server, g = player()
    names = ("MOUNTED_CROSSBOWMAN", "HEAVY_MOUNTED_CROSSBOWMAN", "CAVALRY_ARCHER", "ARCHER")
    old = {n: train.stats(g, n) for n in names}
    rect = train.open_menu(g, "Steve", RANGE)
    assert train.order(g, "Steve", rect, train.layout(g, rect)["CRANEQUINS"][0]) == 1
    train.tick(g, train.seconds(g, "CRANEQUINS"))
    assert "CRANEQUINS" in g.techs
    for n in names[:2]:
        o, s = old[n], train.stats(g, n)
        assert s.range > o.range and s.bonus.get("infantry", 0) > o.bonus.get("infantry", 0), n
        assert s._replace(range=o.range, bonus=o.bonus) == o, n
    for n in names[2:]:
        assert train.stats(g, n) == old[n]
    assert any(c.startswith("aoe stats mc ") for c in server.log), "the live unit"
