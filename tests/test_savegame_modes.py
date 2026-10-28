"""#2981: run.play loads the saved state before the setups of the game modes and before the minimap squares, so
Defend the Wonder, Regicide, Sudden Death and the minimap of Paper see the saved game."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import build  # noqa: E402
import combat  # noqa: E402
import defend_wonder  # noqa: E402
import gather  # noqa: E402
import regicide  # noqa: E402
import run  # noqa: E402
import savegame  # noqa: E402
import sudden_death  # noqa: E402
import train  # noqa: E402
from test_defend_wonder import game as wonder_game  # noqa: E402
from test_empire_wars import town_map  # noqa: E402
from test_game_minimap_buildings import game as minimap_game  # noqa: E402
from test_play_speed import FakeGame  # noqa: E402
from test_regicide import game as regicide_game  # noqa: E402


def test_play_loads_the_state_before_the_mode_setups_and_the_minimap(tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text('{"players": {}, "tile_size": 4, "objects": []}')
    calls = []

    class FakeGather:
        bots, villagers, units, ended, speed, sites = (), {}, [], None, 1.0, []

        def __init__(self, game, data, **k):
            self.data = data

        def setup(self):
            pass

        def run(self, seconds):
            calls.append("run")

    def load(g, d):
        calls.append("load")
        g.towns = {1, 2}                                               # savegame VICTORY

    def stub(name):
        def setup(g, mode, start=True):
            calls.append(name)
            if name == "sudden_death":
                g.towns = set()                                        # its setup would start the towns again
        return setup
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    monkeypatch.setattr(savegame, "load", load)
    monkeypatch.setattr(defend_wonder, "setup", stub("defend_wonder"))
    monkeypatch.setattr(regicide, "setup", stub("regicide"))
    monkeypatch.setattr(sudden_death, "setup", stub("sudden_death"))
    monkeypatch.setattr(build, "minimap", lambda g: calls.append("minimap") or [])
    game = FakeGame()
    game.kind = "paper"
    g = run.play(game, str(tmp_path), state={"players": {}}, mode="defend-the-wonder", regicide=True,
                 sudden_death=True)
    assert calls == ["load", "defend_wonder", "regicide", "minimap", "run"]   # Sudden Death: "loaded": "skip"
    assert g.towns == {1, 2}                                           # the saved towns stay


def test_a_loaded_defend_the_wonder_finds_its_wonder_and_ends_when_it_falls():
    state = savegame.dump(wonder_game())
    g = town_map()
    g.players = g.data["players"] = {"1": {"color": "blue"}, "2": {"color": "red"}}
    g.mode = "defend-the-wonder"
    savegame.load(g, state)
    defend_wonder.setup(g, start=False)
    site = next(s for s in g.sites if s["name"] == "WONDER")
    x0, x1, z0, z1 = site["footprint"]
    assert g.wonder == combat.target_uuid([x0, z0, x1, z1])
    g.wonders_gone = {g.wonder}                                        # wonder.tick: its target is gone
    defend_wonder.tick(g)
    assert g.ended == "Defeat"                                         # player 1 defends: the attackers win


def test_a_defeated_player_of_a_loaded_regicide_gets_no_king(monkeypatch):
    server, g, spy = regicide_game(king2=False)
    monkeypatch.setattr(train, "summon", spy)
    g.defeated = {2}                                                   # its King died before the save
    regicide.setup(g, start=False)
    assert [s for s in server.summoned if s[1] == 2] == []             # no King, no villagers
    assert ("KING", 1) in [s[:2] for s in server.summoned] and g.kings == {1}
    assert not [s for s in g.sites if s["player"] == 2]                # no free Castle site


def test_the_minimap_of_a_loaded_game_has_no_razed_building():
    _, g = minimap_game()
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": (4, 6, 14, 16)})   # a site of the save
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": (0, 2, 0, 2)})     # razed before the save
    g.razed = {combat.target_uuid([0, 0, 2, 2]): "", combat.target_uuid([10, 10, 12, 12]): ""}   # and a start house
    assert build.minimap(g) == ["aoe minimap building 2 10 4 12 p1", "aoe minimap building 4 14 6 16 p1"]
