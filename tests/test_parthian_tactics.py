"""game/train.py: the archery range researches Parthian Tactics (#1505, AoE2 DE wiki "Parthian Tactics"): Imperial
Age, the mounted archers (also the Arambai, not the Genitour) get more melee and pierce armor and more attack against
the spearman line; not for the civilizations without it (civs.MISSING)."""
import test_castle_upgrades
from menu_line import item
from test_castle_upgrades import RANGE, setup
from test_forging import menus

import buildings
from game import train

NO = set(train.civs.MISSING["PARTHIAN_TACTICS"])

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def player(civ=None, ages=IMPERIAL):
    server, g = setup(ages=ages, techs=())
    if civ:
        g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_archery_range_menu_has_parthian_tactics_in_the_imperial_age():
    server, g = player(ages=("FEUDAL_AGE", "CASTLE_AGE"))
    train.open_menu(g, "Steve", RANGE)
    assert "Parthian Tactics" not in menus(server)[-1] and train.queue(g, "Steve", RANGE, "PARTHIAN_TACTICS") is None
    server, g = player()
    train.open_menu(g, "Steve", RANGE)
    assert item(menus(server)[-1], "Parthian Tactics").endswith(" · research")


def test_the_mounted_archers_get_armor_and_attack_against_spearmen(monkeypatch):
    monkeypatch.setattr(test_castle_upgrades, "LIVE", test_castle_upgrades.LIVE + (("h", "CAVALRY_ARCHER"),))
    server, g = player()
    names = ("CAVALRY_ARCHER", "HEAVY_CAVALRY_ARCHER", "MANGUDAI", "CAMEL_ARCHER", "ARAMBAI", "GENITOUR", "ARCHER",
             "KNIGHT")
    old = {n: train.stats(g, n) for n in names}
    rect = train.open_menu(g, "Steve", RANGE)
    slot = int(item(menus(server)[-1], "Parthian Tactics").split(":")[0])
    assert train.order(g, "Steve", rect, slot) == 1
    train.tick(g, train.seconds(g, "PARTHIAN_TACTICS", "ARCHERY_RANGE"))
    assert "PARTHIAN_TACTICS" in g.techs
    for n in names[:5]:
        o, s = old[n], train.stats(g, n)
        assert s.melee > o.melee and s.pierce > o.pierce and s.bonus.get("spearman", 0) > o.bonus.get("spearman", 0), n
        assert s._replace(melee=o.melee, pierce=o.pierce, bonus=o.bonus) == o, n
    for n in ("GENITOUR", "ARCHER", "KNIGHT"):
        assert train.stats(g, n) == old[n]
    stats = [c for c in server.log if c.startswith("aoe stats ")]
    assert any(" h " in c + " " for c in stats) and not any(" c " in c + " " for c in stats), stats   # the live units


def test_not_for_the_civilizations_without_it():
    server, g = player(min(NO))
    train.open_menu(g, "Steve", RANGE)
    assert "Parthian Tactics" not in menus(server)[-1] and train.queue(g, "Steve", RANGE, "PARTHIAN_TACTICS") is None
    server, g = player(min(set(buildings.CIV_TO_ARCH) - NO))
    train.open_menu(g, "Steve", RANGE)
    assert ":book:Parthian Tactics:" in menus(server)[-1]
