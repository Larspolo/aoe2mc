"""#2543 (epic #2538): in `run.py --play --mode scenario` each computer player of the scenario (aoe2mc.json "players"
"computer", #2539) is a bot of the game program, as the AI players of AoE2 DE. A human seat that no person takes stays
idle."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import bot  # noqa: E402
import combat  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402
import scenario  # noqa: E402

PLAYERS = {"0": {}, "1": {"team": 1, "computer": False}, "2": {"team": 2, "computer": False},
           "3": {"team": 1, "computer": True}, "4": {"team": 2, "computer": True}}


def test_each_computer_player_gets_a_bot_with_a_foe_that_is_not_its_ally():
    seats = scenario.bot_seats(PLAYERS, people=1)
    assert seats == [(3, 2), (4, 1)]
    assert all(not gather.allied(PLAYERS, b, foe) for b, foe in seats)


def test_no_computer_player_gives_no_bot():
    assert scenario.bot_seats({"0": {}, "1": {}, "2": {"computer": False}}, people=1) == []


def test_a_person_takes_a_computer_seat_before_the_bot():
    assert scenario.bot_seats(PLAYERS, people=3) == [(4, 1)]


class FakeGame:
    kind, game_port, version, sides = "vanilla", 0, "26.3", {}

    def forceload(self):
        pass

    def command(self, c):
        pass


def play(tmp_path, monkeypatch, players, **settings):
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"players": players, "tile_size": 4}))
    started, gathers = [], []

    class FakeGather:
        bots, villagers, units, ended, speed, stock, pop_limit = (), [], [], None, 1.0, {}, 200

        def __init__(self, game, data, player=1, **k):
            self.data, self.player, self.players = data, player, data["players"]
            gathers.append(self)

        def setup(self):
            return self

        def run(self, seconds):
            pass

    class FakeBot:
        def __init__(self, game, data, player, foe, **k):
            self.g = FakeGather(game, data, player)
            started.append((player, foe))

        def setup(self):
            return self
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(bot, "Bot", FakeBot)
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    monkeypatch.setattr(scenario, "setup", lambda g, mode, start=True: g)
    run.play(FakeGame(), str(tmp_path), **settings)
    return started


def test_the_scenario_mode_starts_the_bots_of_the_computer_players(tmp_path, monkeypatch):
    assert play(tmp_path, monkeypatch, PLAYERS, mode="scenario") == [(3, 2), (4, 1)]


def test_the_scenario_mode_starts_no_bot_without_a_computer_player(tmp_path, monkeypatch):
    players = {"0": {}, "1": {"computer": False}, "2": {"computer": False}}
    assert play(tmp_path, monkeypatch, players, mode="scenario", bot=True) == []


def test_the_other_modes_keep_the_bot_option(tmp_path, monkeypatch):
    assert play(tmp_path, monkeypatch, PLAYERS, bot=True) == [(2, 1)]
    assert play(tmp_path, monkeypatch, PLAYERS) == []
