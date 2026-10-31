"""The text buffer of the up-store-*-name actions: the map name, a technology name and a type name (#5039)."""
import json

from test_bot_gather import bot_map

from game import per


def stored(text, map_name=None):
    """Run the rules of text on a bot of the map; map_name sets the map of aoe2mc.json (None: no map name)."""
    server, me, b = bot_map()
    if map_name is None:
        b.g.data.pop("map", None)
    else:
        b.g.data["map"] = map_name
    s = per.Script(per.parse(text), b)
    s.step()
    return s, server


def chats(server):
    return [json.loads(c.split(" ", 2)[2])["text"] for c in server.log if c.startswith("tellraw")]


def test_up_store_map_name_gives_the_map_of_the_scenario():
    s, server = stored("(defrule (true) => (up-store-map-name \"\") (up-chat-data-to-all \"map %s\" c: 0) (disable-self))",
                       map_name="Arabia")
    assert s.text == "Arabia"
    assert chats(server)[0].endswith("map Arabia")


def test_up_store_map_name_gives_the_empty_text_without_a_map_name():
    s, _ = stored('(defrule (true) => (up-store-map-name "") (disable-self))')
    assert s.text == ""


def test_up_store_tech_name_gives_the_script_name_of_the_technology():
    s, server = stored('(defrule (true) => (up-store-tech-name c: loom) (up-chat-data-to-all "tech %s" c: 0) (disable-self))')
    assert s.text == "loom"
    assert chats(server)[0].endswith("tech loom")


def test_up_store_tech_name_gives_the_empty_text_for_an_aoe2_id():
    s, _ = stored("(defrule (true) => (up-store-tech-name c: 22) (disable-self))")
    assert s.text == ""


def test_up_store_type_name_gives_the_script_name_of_the_type():
    s, server = stored('(defrule (true) => (up-store-type-name c: villager) (up-chat-data-to-all "type %s" c: 0) (disable-self))')
    assert s.text == "villager"
    assert chats(server)[0].endswith("type villager")


def test_up_store_type_name_gives_the_empty_text_for_an_aoe2_id():
    s, _ = stored("(defrule (true) => (up-store-type-name c: 83) (disable-self))")
    assert s.text == ""
