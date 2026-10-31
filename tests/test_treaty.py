"""#2297: `run.py --play --treaty MM:SS`, the AoE2 setting "Treaty length": before it no player can attack another."""
import importlib
import json
import types

from test_bot_attack import armed, orders

from game import run, treaty


def clicked(me, server, target="m0"):
    """Player Steve of me right clicks the enemy unit target with a selected militia; the new commands."""
    start = len(server.log)
    server.entities["s1"] = {"Pos": (6.5, 64.0, 8.5), "Rotation": (0.0, 0.0)}
    me.soldiers["s1"], me.selected = "MILITIA", {"s1"}
    me.looks["Steve"] = ((6.5, 65.6, 6.5), (1.0, 0.0, 0.0))
    me.target = lambda *a: ("enemy", target, {(0, 0)})
    me.click("Steve")
    return server.log[start:]


def test_an_attack_order_during_the_treaty_does_nothing_and_shows_a_chat_line():
    server, me, b = armed()
    treaty.start(me, 600.0)
    out = clicked(me, server)
    assert orders(server) == []
    assert any(c.startswith("tellraw Steve ") and '"translate": "aoe2mc.treaty.refuse"' in c and '"with": ["10:00"]' in c for c in out)


def test_after_the_treaty_the_order_attacks_and_a_chat_line_says_so():
    server, me, b = armed()
    treaty.start(me, 60.0)
    treaty.tick(me, 59.0)
    assert treaty.holds(me) and not any("treaty ended" in c for c in server.log)
    treaty.tick(me, 2.0)
    assert any(c.startswith("tellraw @a ") and "treaty ended" in c for c in server.log)
    clicked(me, server)
    assert any(o[-1] == "m0" for o in orders(server))


def test_the_treaty_runs_in_the_game_loop_of_all_gathers():
    server, me, b = armed()
    treaty.start(me, 1.0)
    assert treaty.holds(b.g)                                           # the bot shares the game
    me.run(until=lambda: not treaty.holds(me))
    assert not treaty.holds(b.g)


def test_the_truce_makes_each_player_neutral_to_all_others():
    assert treaty.truce_command({1, 2, 3}) == "aoe neutral p1:p2,p3 p2:p1,p3 p3:p1,p2"


def test_the_bot_does_not_attack_before_the_end_of_the_treaty(tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"players": {"1": {}, "2": {}}, "tile_size": 4}))
    seen = {}

    class FakeGather:
        bots, villagers, units, ended, speed, paper, player = (), [], [], None, 1.0, False, 1

        def __init__(self, game, data, **k):
            self.game, self.data = game, data

        def setup(self):
            return self

        def command(self, c):
            pass

        def run(self, seconds):
            pass

    class FakeBot:
        def __init__(self, *a, attack, **k):
            seen["attack"], self.g = attack, types.SimpleNamespace(villagers=[])

        def setup(self):
            return self
    mod = importlib.import_module                                     # the modules that run.play imports
    monkeypatch.setattr(mod("gather"), "Gather", FakeGather)
    monkeypatch.setattr(mod("bot"), "Bot", FakeBot)
    monkeypatch.setattr(mod("combat"), "setup", lambda game, data: None)
    game = types.SimpleNamespace(kind="vanilla", game_port=0, version="26.3", sides={}, forceload=lambda: None,
                                 command=lambda c: None)
    run.play(game, str(tmp_path), bot=True, bot_attack="5:00", treaty="20:00")
    assert seen["attack"] == 1200.0
    run.play(game, str(tmp_path), bot=True, bot_attack="25:00", treaty="20:00")
    assert seen["attack"] == 1500.0
