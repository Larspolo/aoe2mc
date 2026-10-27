"""game/build.py: the player builds a market in the Feudal Age, as in AoE2 DE (#1251). Fake server."""
from test_build_menu import villager_map

from game import build, combat, train


def test_the_build_menu_has_the_market_with_its_aoe2_cost_and_time():
    assert build.items()[build.MENU.index("MARKET")][1:] == ("barrel", "Market", "175 wood\n60 s")


def test_the_market_is_gray_in_the_dark_age():
    server, g = villager_map()
    icon, _, lore = build.items(g)[build.MENU.index("MARKET")][1:]
    assert icon == "gray_dye" and lore.endswith("Needs the Feudal Age")
    g.techs.add("FEUDAL_AGE")
    assert build.items(g)[build.MENU.index("MARKET")][1] == "barrel"


def test_the_market_has_the_aoe2_hit_points_and_armor():
    s = combat.stats("MARKET")
    assert (s.hp, s.melee, s.pierce, s.classes) == (1800, 1, 8, ("building",))


def test_a_complete_market_counts_for_the_castle_age():
    server, g = villager_map()
    g.techs.add("FEUDAL_AGE")
    g.sites += [{"name": n, "player": g.player, "done": True} for n in ("BLACKSMITH", "MARKET")]
    assert train.missing(g, "CASTLE_AGE") is None
