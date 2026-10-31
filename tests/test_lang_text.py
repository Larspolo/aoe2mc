"""#5344: the end titles and the age up message are translate components with the English fallback of
game/data/texts.jsonl, so that a lang file of a resource pack can give another language."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import cheats  # noqa: E402
import lang  # noqa: E402
import train  # noqa: E402
from test_scenario_mode import game  # noqa: E402


def component(command):
    return json.loads(command[command.index("{"):])


def test_text_gives_the_key_the_fallback_and_the_arguments(monkeypatch):
    monkeypatch.setattr(lang, "EN_US", {"aoe2mc.t": "A %s and %s", "aoe2mc.u": "B"})
    assert lang.text("aoe2mc.t", 1, "x", color="red") == {"translate": "aoe2mc.t", "fallback": "A %s and %s",
                                                          "with": ["1", "x"], "color": "red"}
    assert lang.text("aoe2mc.u") == {"translate": "aoe2mc.u", "fallback": "B"}
    with pytest.raises(KeyError):
        lang.text("aoe2mc.none")
    with pytest.raises(ValueError):
        lang.text("aoe2mc.t", 1)


def test_the_end_title_and_the_age_up_message_carry_a_key_of_the_data():
    server, g, _ = game({"0": {}, "1": {}, "2": {}})
    cheats.over(g, lambda n: n == 1)
    train.research(g, {"name": "FEUDAL_AGE", "player": "@a"})
    shown = [component(c) for c in server.log
             if c.startswith("title @a[team=p") and " title {" in c and "translate" in c or c.startswith("tellraw @a {\"translate")]
    keys = {c["translate"] for c in shown}
    assert {"aoe2mc.victory", "aoe2mc.defeat", "aoe2mc.age_up"} <= keys
    assert all(c["fallback"] == lang.en_us()[c["translate"]] for c in shown
               if not c["translate"].startswith("aoe2mc.tech."))      # an age name comes from the tables (#5346)
