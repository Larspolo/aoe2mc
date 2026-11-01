"""--takeover P > 1: a bot plays each other player of the record, also the players below P (#5476)."""
import types

import pytest
import savegame

from game import bot, run


class Stop(Exception):
    pass


def test_takeover_2_gives_bots_to_players_1_and_3(monkeypatch, tmp_path):
    import bot as bots
    import combat
    import gather as gathers
    from test_play_speed import FakeGame
    made, seen = [], []

    class FakeGather:
        bots, villagers, units, ended, speed, peers = (), [], [], None, 1.0, []

        def __init__(self, game, data, player=1, **k):
            self.player, self.map, self.relics = player, types.SimpleNamespace(trees={}, bushes={}, mines={}), []
            made.append(self)

        def setup(self):
            pass

    class Stub:
        def __init__(self, player):
            self.g = types.SimpleNamespace(villagers=[], player=player)

        def setup(self):
            return self

    def bot_of(game, data, **kw):
        seen.append((kw["player"], kw["own"]))
        if len(seen) == 2:
            raise Stop
        return Stub(kw["player"])

    monkeypatch.setattr(bots, "Bot", bot_of)
    monkeypatch.setattr(gathers, "Gather", FakeGather)
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    monkeypatch.setattr(run, "start_places", lambda data: ({}, {}))
    (tmp_path / "aoe2mc.json").write_text('{"players": {"0": {}, "1": {}, "2": {}, "3": {}}, "tile_size": 4}')
    game = FakeGame()
    game.seats = (2,)
    with pytest.raises(Stop):
        run.play(game, str(tmp_path), bot="all", people=1)
    assert [x.player for x in made] == [1, 2]                  # the Gather of player 1 and the Side of the person
    assert seen == [(1, made[0]), (3, None)]                   # the bot of player 1 plays its Gather


def test_the_bot_of_player_1_does_not_step_its_gather_twice():
    steps = []
    b = object.__new__(bot.Bot)
    b.g, b.own, b.orders = types.SimpleNamespace(step=lambda: steps.append(1)), True, lambda: steps.append(0)
    b.step()
    assert steps == [0]


def test_bots_again_gives_player_1_its_replay_state():
    g = types.SimpleNamespace(bots=[types.SimpleNamespace(charged=False, g=types.SimpleNamespace(player=1),
                                                          difficulty="standard", foe=None, attack=0)])
    savegame.bots_again(g, {"players": {"1": {"bot": {"foe": 3, "attack": 720, "charged": True}}}})
    b = g.bots[0]
    assert (b.foe, b.attack, b.charged) == (3, 720, True)
