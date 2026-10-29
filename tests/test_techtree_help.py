"""The tooltip of a tech tree item shows its help line one time (#3729): the plugin adds it (train.lore, #1160)."""
import sys
import types

sys.path.insert(0, "game")
import techtree  # noqa: E402
import train  # noqa: E402


def test_the_item_text_has_no_help_line_that_the_plugin_adds_again():
    g = types.SimpleNamespace(data={"players": {"1": {"civ": "BRITONS"}}}, player=1, techs=set(), age=0)
    material, label, text = techtree.item(g, "BARRACKS", "MILITIA")
    assert (material, label) == (train.ITEMS["MILITIA"][1], train.ITEMS["MILITIA"][2])   # the key of the aoe lore line
    assert train.HELP["MILITIA"] not in text and "food" in text
