"""#2406: `run.py --play --mode wonder-race`, the AoE2 DE game mode "Wonder Race": no player can attack another
player, and the first player with a complete wonder wins."""
import importlib
import json
import math
import types

from test_bot_attack import armed, orders
from test_cheat_end import game
from test_treaty import clicked
from test_wonder import SITE, targets, tick

from game import combat, run, treaty


def test_an_attack_order_does_nothing_for_the_whole_game():
    server, me, b = armed()
    treaty.start(me, math.inf)
    assert any("no player can attack another player in this game" in c for c in server.log)
    treaty.tick(me, 1e9)
    out = clicked(me, server)
    assert orders(server) == [] and treaty.holds(b.g)
    assert any(c.startswith("tellraw Steve ") and "cannot attack in this game" in c for c in out)
    assert not any("treaty ended" in c for c in server.log)


def race(site):
    server, g = game()
    g.mode = "wonder-race"
    x0, x1, z0, z1 = site["footprint"]
    targets(server, {combat.target_uuid([x0, z0, x1, z1])})
    g.sites.append(dict(site))
    tick(g, 0)
    return server, g


def test_the_first_complete_wonder_wins_at_once():
    server, g = race(SITE)
    assert g.ended == "Victory" and 'title @a[team=p1] title {"translate":"aoe2mc.victory","fallback":"Victory","color":"gold"}' in server.log
    assert "bossbar remove aoe2mc:wonder_p1" in server.log


def test_the_wonder_of_a_rival_ends_the_game_with_defeat_at_once():
    server, g = race({**SITE, "player": 2})
    assert g.ended == "Defeat" and 'title @a[team=p1] title {"translate":"aoe2mc.defeat","fallback":"Defeat","color":"red"}' in server.log


def test_an_unfinished_wonder_does_not_win():
    server, g = race({**SITE, "done": False, "progress": 0.5})
    assert not g.ended


def test_in_the_standard_mode_a_wonder_still_needs_its_timer():
    server, g = game()
    targets(server, {combat.target_uuid([4, 4, 9, 9])})
    g.sites.append(dict(SITE))
    tick(g, 0)
    assert not g.ended


def test_play_starts_an_endless_treaty_and_the_bot_never_attacks(tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"players": {"1": {}, "2": {}}, "tile_size": 4}))
    seen = {}

    class FakeGather:
        bots, villagers, units, ended, speed, paper, player, mode = (), [], [], None, 1.0, False, 1, "standard"

        def __init__(self, game, data, **k):
            self.game, self.data = game, data

        def setup(self):
            seen["g"] = self
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
    def new():
        return types.SimpleNamespace(kind="vanilla", game_port=0, version="26.3", sides={}, forceload=lambda: None,
                                     command=lambda c: None)
    run.play(new(), str(tmp_path), bot=True, bot_attack="5:00", mode="wonder-race")
    assert seen["attack"] == math.inf and seen["g"].mode == "wonder-race" and treaty.holds(seen["g"])
    run.play(new(), str(tmp_path), bot=True, bot_attack="5:00")
    assert seen["attack"] == 300.0 and not treaty.holds(seen["g"])
