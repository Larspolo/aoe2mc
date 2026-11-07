"""The color mood of the map in the options menu of the editor (#6086): a click sets the next mood and shows it."""
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
import export  # noqa: E402

import aoe2mc  # noqa: E402


class Fake:
    def __init__(self):
        self.sent, self.menus, self.player, self.data = [], {}, 2, {"players": {}}

    def command(self, cmd):
        self.sent.append(cmd)
        return ""


def test_each_click_sets_the_next_mood_and_sends_its_commands(monkeypatch):
    monkeypatch.setattr(editor, "icons", lambda: {})
    g = Fake()
    editor.options_menu(g, "p")
    keys = list(aoe2mc.MOODS)
    mood = "DEFAULT"
    for _ in range(len(keys)):
        g.sent.clear()
        g.menus["p"]("p", editor.MOOD_SLOT, False)
        mood = keys[(keys.index(mood) + 1) % len(keys)]
        assert g.data["mood"] == mood
        assert f"time set {aoe2mc.MOODS[mood]}" in g.sent
        assert f"weather {'rain' if mood in aoe2mc.RAIN else 'clear'}" in g.sent


def test_the_export_has_the_mood():
    from AoE2ScenarioParser.datasets.trigger_lists import ColorMood
    mood = next(k for k in aoe2mc.MOODS if k != "DEFAULT" and k in ColorMood.__members__)
    mm = types.SimpleNamespace(map_color_mood=None)
    scn = types.SimpleNamespace(map_manager=mm, player_manager=types.SimpleNamespace(players={}))
    export.options(scn, {"mood": mood, "players": {}}, [])
    assert mm.map_color_mood == ColorMood[mood]
