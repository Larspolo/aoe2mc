"""game/civs.py MISSING: Guilds only for the civilizations that have it in AoE2 DE (#1931). The AoE2 wiki "Guilds",
availability chart, revision 1088694: 0 or -1 (had it in the past) for the 18 civilizations below."""
from test_loom import menus
from test_market_techs import market_map

from game import civs, market, train

WIKI = {"AZTECS", "BULGARIANS", "CHINESE", "DANES", "FRANKS", "GURJARAS", "HINDUSTANIS", "JAPANESE", "KHMER", "MAGYARS",
        "MAPUCHE", "MONGOLS", "POLES", "SARACENS", "SLAVS", "TUPI", "VIKINGS", "WEI"}


def guilds(civ):
    """True when the Imperial Age market menu of a player of civ shows Guilds."""
    server, g = market_map(3)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    train.open_menu(g, "Steve", (3, 3))
    return ":book:Guilds:" in menus(server)[-1]


def test_the_civilizations_without_guilds_are_those_of_the_wiki_chart():
    assert set(civs.MISSING["GUILDS"]) == WIKI and len(WIKI) == 18


def test_the_saracens_franks_and_hindustanis_do_not_see_guilds_and_the_britons_do():
    assert [c for c in ("SARACENS", "FRANKS", "HINDUSTANIS", "BRITONS") if guilds(c)] == ["BRITONS"]


def test_the_saracens_keep_their_trading_fee():
    assert market.CIV_FEES["SARACENS"] == 5
