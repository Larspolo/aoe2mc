"""#5373 (#5343): the chat lines and titles of the game modes are translate components with the English fallback of
game/data/texts.jsonl, so that a lang file of a resource pack can give them in another language."""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import battle_royale  # noqa: E402
import conquest  # noqa: E402
import diplomacy  # noqa: E402
import lang  # noqa: E402
import relic_victory  # noqa: E402
import treaty  # noqa: E402
from test_battle_royale import fake  # noqa: E402
from test_cheat_end import game as cheat_game  # noqa: E402
from test_king_of_the_hill import run  # noqa: E402
from test_king_of_the_hill import setup as hill_setup
from test_lock_speed import setup as speed_setup  # noqa: E402
from test_relic_victory import HOME  # noqa: E402
from test_relic_victory import start as relic_start
from test_treaty import armed  # noqa: E402
from test_wonder import start as wonder_start  # noqa: E402


def components(log, key):
    """The translate components of the key among the command lines of the log (a chat line or a title)."""
    out = []
    for c in log:
        if '"translate"' in c and "{" in c:
            comp = json.loads(c[c.index("{"):])
            if isinstance(comp, dict) and comp.get("translate") == key:
                out.append(comp)
    return out


def assert_text(log, key):
    """The line of the key is in the table of texts, and its fallback is the English text of the table."""
    assert key in lang.EN_US, key
    comps = components(log, key)
    assert comps, f"no line of {key}"
    assert all(c["fallback"] == lang.EN_US[key] for c in comps)
    return comps


def test_conquest_defeat_sends_its_key_and_the_defeat_title():
    server, g = cheat_game()
    conquest.defeat(g, 2)
    assert_text(server.log, "aoe2mc.conquest.defeated")
    assert_text(server.log, "aoe2mc.defeat")


def test_wonder_built_sends_the_key_with_the_player_as_argument():
    server, g, _, _ = wonder_start()
    comps = assert_text(server.log, "aoe2mc.wonder.built")
    assert comps[0]["with"] == ["1"]


def test_relic_holder_sends_the_key_of_all_relics():
    server, g = relic_start()
    g.relics[0].update(at=None, home=HOME)                             # all relics in an own monastery
    relic_victory.tick(g, 0)
    assert_text(server.log, "aoe2mc.relic_victory.all")


def test_monument_owner_sends_the_key_of_the_monument():
    server, g = hill_setup(("u1", 1, 16.0, 16.0))
    run(g, 1)
    assert_text(server.log, "aoe2mc.hill.holds")


def test_battle_royale_start_sends_the_key_with_the_minutes():
    g = battle_royale.setup(fake())
    comps = assert_text(g.log, "aoe2mc.battle_royale.start")
    assert comps[0]["with"] == [f"{battle_royale.MINUTES}:00"]


def test_treaty_start_and_refusal_send_the_keys_with_the_end():
    server, me, _ = armed()
    treaty.start(me, 600.0)
    comps = assert_text(server.log, "aoe2mc.treaty.start")
    assert comps[0]["with"] == ["10:00"] and comps[0]["color"] == "yellow"
    treaty.refuse(me, "Steve")
    assert_text(server.log, "aoe2mc.treaty.refuse")


def test_a_treaty_with_no_end_sends_the_endless_key():
    server, me, _ = armed()
    treaty.start(me, math.inf)
    assert_text(server.log, "aoe2mc.treaty.start_endless")
    assert not components(server.log, "aoe2mc.treaty.start")


def test_game_speed_sends_the_key_with_the_speed_as_argument():
    server, g = speed_setup(True)
    diplomacy.faster(g)
    comps = assert_text(server.log, "aoe2mc.diplomacy.speed")
    assert comps[0]["with"][1] == f"{g.speed:g}"


def test_the_diplomacy_words_are_keys_of_the_table():
    for kind in diplomacy.STANCES:
        assert lang.text(f"aoe2mc.diplomacy.{kind}")["translate"] in lang.EN_US
    for res in diplomacy.RESOURCES:
        assert lang.text(f"aoe2mc.resource.{res}")["fallback"] == lang.EN_US[f"aoe2mc.resource.{res}"]
