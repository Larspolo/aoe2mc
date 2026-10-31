"""#5346: the names of units, technologies and ages in the boss bar, the train menu and the age up message are
translate keys (aoe2mc.unit.*, aoe2mc.tech.*) with the English name as fallback."""
import json
import os
import sys
from urllib.parse import unquote

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import lang  # noqa: E402
import train  # noqa: E402
from test_bossbar import setup as bar_setup  # noqa: E402
from test_lang_text import component  # noqa: E402
from test_scenario_mode import game  # noqa: E402
from test_wheelbarrow import setup as tc_setup  # noqa: E402

import units  # noqa: E402


def test_name_gives_the_key_and_the_pretty_fallback():
    assert lang.name("VILLAGER_MALE") == {"translate": "aoe2mc.unit.VILLAGER_MALE", "fallback": units.pretty("VILLAGER_MALE")}
    assert lang.name("LOOM", "tech", "Loom") == {"translate": "aoe2mc.tech.LOOM", "fallback": "Loom"}
    assert lang.plain(lang.text("aoe2mc.age_up", 1, lang.name("FEUDAL_AGE", "tech", "Feudal Age"))) == \
        lang.EN_US["aoe2mc.age_up"].replace("%s", "1", 1).replace("%s", "Feudal Age")


def test_the_boss_bar_of_a_villager_carries_a_unit_key():
    server, g = bar_setup()
    g.select("v")
    c = next(c for c in server.log if c.startswith("bossbar set aoe2mc:sel_p1 name "))
    assert json.loads(c.split(" name ", 1)[1])[0] == lang.name("VILLAGER_MALE")


def test_the_train_menu_items_carry_unit_and_tech_keys():
    """The plugin keeps the key of each menu item name from `aoe lore` and shows the name as its fallback."""
    server, g = tc_setup(food=1000, wood=1000)
    train.lore(g)
    sent = {unquote(c.split()[3]): c.split()[5] for c in server.log if c.startswith("aoe lore ") and len(c.split()) == 6}
    assert sent[train.ITEMS["VILLAGER_MALE"][2]] == lang.name("VILLAGER_MALE")["translate"] == "aoe2mc.unit.VILLAGER_MALE"
    assert sent[train.ITEMS["LOOM"][2]] == "aoe2mc.tech.LOOM"


def test_the_age_up_message_carries_the_tech_key_of_the_age():
    server, g, _ = game({"0": {}, "1": {}, "2": {}})
    train.research(g, {"name": "FEUDAL_AGE", "player": "@a"})
    c = next(component(c) for c in server.log if c.startswith('tellraw @a {"translate": "aoe2mc.age_up"'))
    assert c["with"][1] == {"translate": "aoe2mc.tech.FEUDAL_AGE", "fallback": train.AGES[1]}
