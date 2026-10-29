"""#2267: `run.py --play --civ 1=CHINESE` sets the civilization of a player before the game starts."""
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import civs  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402


class FakeGame:
    kind, game_port, version, sides = "vanilla", 0, "26.3", {}

    def forceload(self):
        pass

    def command(self, c):
        pass


def gathers(tmp_path, monkeypatch, civ):
    """(civilization of player 1, of player 2, start resources of player 1) of the Gather that play() makes, with no
    server."""
    players = {"1": {"civ": "BRITONS"}, "2": {"civ": "FRANKS"}}
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"players": players, "tile_size": 4}))
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, game, data, player, **k):
            self.data, self.player = data, player

        def setup(self):
            seen.append(self)

        def run(self, seconds):
            pass
    monkeypatch.setattr(gather, "Gather", FakeGather)
    import combat
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    run.play(FakeGame(), str(tmp_path), civ=civ)
    base = {"food": 200, "wood": 200, "gold": 100, "stone": 200}
    g, = seen
    return civs.civ(g), civs.civ(g, 2), civs.start(g, base)


def test_civ_option_gives_the_chosen_civilization(tmp_path, monkeypatch):
    one, two, start = gathers(tmp_path, monkeypatch, run.civ_choices(["1=chinese"]))
    assert (one, two) == ("CHINESE", "FRANKS")                               # player 2 keeps the scenario civilization
    g = types.SimpleNamespace(data={"players": {"1": {"civ": "CHINESE"}}}, player=1)
    assert start == civs.start(g, {"food": 200, "wood": 200, "gold": 100, "stone": 200})   # the Chinese start bonus


def test_unknown_civ_stops_with_the_names(capsys):
    with pytest.raises(SystemExit) as e:
        run.civ_choices(["1=ATLANTEANS"])
    assert "ATLANTEANS" in str(e.value) and all(r["name"] in str(e.value) for r in civs.ROWS)
    with pytest.raises(SystemExit):
        run.civ_choices(["CHINESE"])
