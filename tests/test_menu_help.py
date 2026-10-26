"""game/train.py (#1160): each menu item has the short AoE2 help text as the last lore line. The plugin keeps the
lines (aoe lore, sent once by train.lore), so the menu commands stay below the RCON limit."""
from urllib.parse import unquote

import pytest
import test_forging

from game import build, train


class Log:
    def __init__(self):
        self.log = []

    def command(self, cmd):
        self.log.append(cmd)
        return ""


def test_each_unit_and_technology_has_a_short_help_line():
    names = {n for b in train.TRAINS.values() for n in b} | (set(train.UNIQUE.values()) & set(train.COSTS))
    names |= {unit for _, unit in train.UPGRADES.values()}
    assert names <= set(train.HELP) <= set(train.ITEMS)
    assert all(0 < len(h) <= 50 for h in train.HELP.values())


def test_lore_sends_the_help_of_padded_archer_armor_for_its_book_and_its_gray_item():
    g = Log()
    train.lore(g)
    sent = [unquote(c) for c in g.log]
    assert len(sent) == 2 * len(train.HELP) and all(c.startswith("aoe lore ") for c in g.log)
    for material in ("book", build.LOCKED):
        assert f"aoe lore {material} Padded Archer Armor Archers +1 melee armor, +1 pierce armor." in sent
    assert sent.index("aoe lore gray_dye Man-at-Arms Upgrades militia to man-at-arms.") > \
        sent.index("aoe lore gray_dye Man-at-Arms Infantry. Strong vs. eagles, buildings.")


@pytest.mark.parametrize("kind", [None, "paper"])
def test_the_setup_sends_the_help_lines_only_to_paper(kind):
    server, g = test_forging.setup()
    server.kind = kind
    g.paper = kind == "paper"
    n = len(server.log)
    g.setup()
    assert any(c.startswith("aoe lore ") for c in server.log[n:]) == (kind == "paper")


@pytest.mark.mc
def test_the_plugin_keeps_the_help_lines(tiny_world, tmp_path):
    import shutil

    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import menu, run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        assert menu.lore(game, "book", "Loom", "Villagers +15 HP, +1/+2 armor.").strip() == "Lore: 1 items"
        train.lore(game)
        assert game.command("aoe lore book Loom x").strip() == f"Lore: {len(train.HELP) + len(train.HELP) - 1} items"
        assert game.command(menu.command("@a", "Town Center", [(1, "book", "Loom", "50 gold")])).strip() == \
            "Menu: 0 players"
