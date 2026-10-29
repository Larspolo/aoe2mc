"""game/civs.py MISSING: Guilds only for the civilizations that have it in AoE2 DE (#1931, the AoE2 wiki "Guilds",
availability chart)."""
from test_loom import menus
from test_market_techs import market_map

from game import civs, train


def guilds(civ):
    """True when the Imperial Age market menu of a player of civ shows Guilds."""
    server, g = market_map(3)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    train.open_menu(g, "Steve", (3, 3))
    return ":book:Guilds:" in menus(server)[-1]


def test_only_the_civilizations_with_guilds_see_it():
    names = ("SARACENS", "FRANKS", "HINDUSTANIS", "BRITONS")
    assert [c for c in names if guilds(c)] == [c for c in names if c not in civs.MISSING["GUILDS"]]
