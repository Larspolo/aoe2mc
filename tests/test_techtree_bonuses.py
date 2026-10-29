"""#3536: slot 46 of the tech tree page of buildings shows the civilization bonuses and the team bonus (the key
"texts" of data/civs.jsonl, the text at the left of the AoE2 DE tech tree)."""
from test_techtree import click, setup

from game import civs, diplomacy, techtree


def test_the_britons_page_has_the_bonuses_in_slot_46_with_the_team_bonus():
    server, g = setup("BRITONS")
    diplomacy.open_menu(g, "Steve")
    text = click(server, g, diplomacy.TECH_TREE_SLOT)
    assert f"{techtree.BONUSES}:written_book:Civilization bonuses:" in text and "49:paper:Britons" in text
    lore = " ".join(text.split(f"{techtree.BONUSES}:written_book:Civilization bonuses:")[1].split(" 4")[0].split())
    assert "Team bonus: Archery Ranges work 10% faster" in lore and "Shepherds work 25% faster" in lore


def test_each_civilization_of_the_game_program_has_bonuses_and_a_team_bonus():
    for r in civs.ROWS:                                            # run.py --civ offers each line of civs.jsonl
        texts = civs.value("texts", r["name"])
        assert texts and texts["bonuses"] and all(texts["bonuses"]) and texts["team"], r["name"]


def test_each_lore_line_is_short_and_each_menu_command_fits_rcon():
    for civ in techtree.CIVS:
        (slot, _, _, lore), = techtree.bonus_items(civ)
        assert slot == techtree.BONUSES and max(map(len, lore.split("\n"))) <= 50, civ
        server, g = setup(civ)
        diplomacy.open_menu(g, "Steve")
        click(server, g, diplomacy.TECH_TREE_SLOT)
        assert all(len(c) <= 1446 for c in server.log if c.startswith("aoe menu")), civ
