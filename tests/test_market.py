"""game/build.py: the player builds a market in the Feudal Age, as in AoE2 DE (#1251). Fake server."""
from test_build_menu import villager_map

from game import build, train


def test_the_market_is_gray_in_the_dark_age():
    server, g = villager_map()
    icon, _, lore = build.items(g)[build.MENU.index("MARKET")][1:]
    assert icon == "gray_dye" and lore.endswith("Needs the Feudal Age")
    g.techs.add("FEUDAL_AGE")
    assert build.items(g)[build.MENU.index("MARKET")][1] == "barrel"


def test_a_complete_market_counts_for_the_castle_age():
    server, g = villager_map()
    g.techs.add("FEUDAL_AGE")
    g.sites += [{"name": n, "player": g.player, "done": True} for n in ("BLACKSMITH", "MARKET")]
    assert train.missing(g, "CASTLE_AGE") is None
