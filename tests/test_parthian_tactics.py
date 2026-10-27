"""game/train.py: the archery range researches Parthian Tactics (#1505, AoE2 DE wiki "Parthian Tactics"): Imperial
Age, 200 food, 250 gold, 65 s, the mounted archers (also the Arambai, not the Genitour) get +1 melee armor, +2 pierce
armor and +2 attack against the spearman line; not for the civilizations without it (civs.MISSING)."""
import test_castle_upgrades
from test_castle_upgrades import RANGE, setup
from test_forging import menus

from game import civs, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def player(civ=None, ages=IMPERIAL):
    server, g = setup(ages=ages, techs=())
    if civ:
        g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_archery_range_menu_has_parthian_tactics_in_the_imperial_age():
    assert train.COSTS["PARTHIAN_TACTICS"] == {"food": 200, "gold": 250}
    assert train.TRAIN_TIMES["PARTHIAN_TACTICS"] == 65 and train.TECH_AGE["PARTHIAN_TACTICS"] == 3
    server, g = player(ages=("FEUDAL_AGE", "CASTLE_AGE"))
    train.open_menu(g, "Steve", RANGE)
    assert "Parthian Tactics" not in menus(server)[-1] and train.queue(g, "Steve", RANGE, "PARTHIAN_TACTICS") is None
    server, g = player()
    train.open_menu(g, "Steve", RANGE)
    assert f" {train.MORE}:book:Parthian Tactics:200 food · 250 gold · 65 s · research " in menus(server)[-1] + " "


def test_the_mounted_archers_get_armor_and_attack_against_spearmen(monkeypatch):
    monkeypatch.setattr(test_castle_upgrades, "LIVE", test_castle_upgrades.LIVE + (("h", "CAVALRY_ARCHER"),))
    server, g = player()
    names = ("CAVALRY_ARCHER", "HEAVY_CAVALRY_ARCHER", "MANGUDAI", "CAMEL_ARCHER", "ARAMBAI", "GENITOUR", "ARCHER",
             "KNIGHT")
    old = {n: train.stats(g, n) for n in names}
    rect = train.open_menu(g, "Steve", RANGE)
    assert train.order(g, "Steve", rect, train.MORE) == 1
    train.tick(g, 65)
    assert "PARTHIAN_TACTICS" in g.techs
    for n in names[:5]:
        o = old[n]
        assert train.stats(g, n) == o._replace(melee=o.melee + 1, pierce=o.pierce + 2,
                                               bonus={**o.bonus, "spearman": o.bonus.get("spearman", 0) + 2})
    s = train.stats(g, "CAVALRY_ARCHER")
    assert (s.melee, s.pierce, s.bonus["spearman"]) == (1, 2, 4)
    for n in ("GENITOUR", "ARCHER", "KNIGHT"):
        assert train.stats(g, n) == old[n]
    stats = [c for c in server.log if c.startswith("aoe stats ")]
    assert any(" h " in c + " " for c in stats) and not any(" c " in c + " " for c in stats), stats   # the live units


def test_not_for_the_civilizations_without_it():
    assert {"BRITONS", "FRANKS", "BENGALIS"} <= set(civs.MISSING["PARTHIAN_TACTICS"])
    assert not {"MONGOLS", "HUNS", "TURKS", "WEI"} & set(civs.MISSING["PARTHIAN_TACTICS"])
    server, g = player("BRITONS")
    train.open_menu(g, "Steve", RANGE)
    assert "Parthian Tactics" not in menus(server)[-1] and train.queue(g, "Steve", RANGE, "PARTHIAN_TACTICS") is None
    server, g = player("MONGOLS")
    train.open_menu(g, "Steve", RANGE)
    assert ":book:Parthian Tactics:" in menus(server)[-1]
