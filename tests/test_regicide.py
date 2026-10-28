"""#2347: `run.py --play --mode regicide` is the AoE2 DE game mode "Regicide" (wiki "Regicide (game mode)"): each
player starts with a King, and a player whose Kings all died is defeated. "standard" (the default): no King."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import regicide  # noqa: E402
import run  # noqa: E402
import train  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402
from test_play_speed import FakeGame  # noqa: E402


def game(king2=True):
    """Players 1 and 2 with a town center each; player 2 has a King on the map, player 3 has no town center."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [2, 2, 6, 6]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 2, "footprint": [12, 12, 16, 16]},
               {"kind": "unit", "name": "MILITIA", "player": 3, "uuid": "m-3", "tile": [18.5, 2.5]}]
    objects += [{"kind": "unit", "name": "KING", "player": 2, "uuid": "k-2", "tile": [10.5, 10.5]}] * king2
    server = FakeServer({"k-2": {"Pos": (10.5, 64.0, 10.5)}, "m-3": {"Pos": (18.5, 64.0, 2.5)}, "Steve": {}})
    g = gather.Gather(server, grid([[64] * 20 for _ in range(20)], objects)).setup()
    g.players = g.data["players"] = {str(p): {"color": "blue", "arch": "western"} for p in (0, 1, 2, 3)}
    g.data.update(tile_size=1, level_height=1)                     # build.found draws the Castle site (#2388)
    owner = {o["uuid"]: o["player"] for o in objects if "uuid" in o}
    server.kings = set()
    command = server.command

    def answer(cmd):
        if cmd.startswith("tag ") and cmd.endswith(f" add {regicide.KING}"):
            server.kings.add(cmd.split()[1])
        if cmd.startswith("execute if entity @e[tag=aoe2mc.p") and regicide.KING in cmd:
            server.log.append(cmd)
            n = int(cmd.split("aoe2mc.p")[1].split(",")[0])
            return "Test passed, count: 1" if any(owner.get(u) == n for u in server.kings) else "Test failed"
        return command(cmd)
    server.command = answer
    summon = train.summon

    def spy(x, name, pos, rotation=1.5, player=None):
        uuid = summon(x, name, pos, rotation, player)
        owner[uuid] = player
        server.summoned.append((name, player, pos))
        return uuid
    server.summoned = []
    return server, g, spy


def check(g):
    g.regicide_at = 0.0                                            # no wait of conquest.EVERY seconds
    regicide.tick(g)


def test_each_player_with_a_town_center_has_one_king(monkeypatch):
    server, g, spy = game()
    monkeypatch.setattr(train, "summon", spy)
    regicide.setup(g)
    assert [(name, player) for name, player, pos in server.summoned if name == "KING"] == [("KING", 1)]   # player 2
    server.summoned = server.summoned[:1]                          # has its own; the villagers: test_regicide_start.py
    (_, _, (x, _, z)), = server.summoned
    assert 1 <= x <= 7 and 1 <= z <= 7                             # next to the town center of player 1
    assert "tag k-2 add aoe2mc.king" in server.log and g.kings == {1, 2}   # player 3: no town center, no King
    assert len(server.kings) == 2 and set(g.villagers) >= server.kings - {"k-2"}   # the own King of the human player


def test_a_loaded_game_gets_no_second_king(monkeypatch):
    server, g, spy = game()
    monkeypatch.setattr(train, "summon", spy)
    regicide.setup(g)
    n = len(server.summoned)
    regicide.setup(g)                                              # the tag stays on the King in the world
    assert len(server.summoned) == n and [u[0] for u in server.summoned].count("KING") == 1   # no more villagers too


def test_the_death_of_a_rival_king_defeats_its_player(monkeypatch):
    server, g, spy = game()
    monkeypatch.setattr(train, "summon", spy)
    regicide.setup(g)
    check(g)
    assert not g.ended and not g.defeated
    server.kings.discard("k-2")
    server.log.clear()
    check(g)
    assert g.defeated == {2} and "aoe destroy @e[tag=aoe2mc.building,team=p2]" in server.log
    assert any("The King of player 2 died" in c for c in server.log)


def test_the_death_of_the_own_king_is_a_defeat(monkeypatch):
    server, g, spy = game()
    monkeypatch.setattr(train, "summon", spy)
    regicide.setup(g)
    server.kings = {"k-2"}
    server.log.clear()
    check(g)
    assert g.ended == "Defeat" and 'title @a[team=p1] title {"text":"Defeat","color":"red"}' in server.log


def test_the_run_loop_checks_the_kings_only_in_regicide(monkeypatch):
    calls = []
    for m in (gather.conquest, gather.fog, gather.herd, gather.regicide):
        monkeypatch.setattr(m, "tick", lambda g, m=m: calls.append(m.__name__))
    monkeypatch.setattr(gather.wonder, "tick", lambda g, dt: None)
    monkeypatch.setattr(gather.relic_victory, "tick", lambda g, dt: None)
    monkeypatch.setattr(gather.score, "tick", lambda g: None)          # not a win (#2355)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    for mode, kings in ((None, 0), ("standard", 0), ("regicide", 3)):
        calls.clear()
        g = object.__new__(gather.Gather)
        g.tick, g.bots, g.ended = 0.25, (), None
        if mode:
            g.mode = mode
        g.point = g.step = lambda: None
        g.clicks = lambda: ()
        g.run(until=lambda: calls.count("conquest") >= 3)
        assert calls.count("regicide") == kings


@pytest.mark.parametrize("mode", ["standard", "regicide"])
def test_play_sets_up_the_mode(mode, tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text('{"players": [], "tile_size": 4}')
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

        def run(self, seconds):
            seen.append(getattr(self, "mode", "standard"))
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(regicide, "setup", lambda g, m, start: seen.append(f"setup {m} {start}"))
    import combat
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    run.play(FakeGame(), str(tmp_path), mode=mode)
    assert seen == (["setup regicide True", "regicide"] if mode == "regicide" else ["standard"])


def test_the_mode_option_goes_to_play(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    seen = {}
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(start=lambda: None, stop=lambda: None,
                                                                         port=0))
    monkeypatch.setattr(run, "play", lambda *a, **k: seen.update(k) or types.SimpleNamespace(ended=None))
    monkeypatch.setattr(run, "console", lambda game: None)
    run.main([str(tmp_path), "--play", "--mode", "regicide"])
    assert seen["mode"] == "regicide"
    run.main([str(tmp_path), "--play"])
    assert seen["mode"] == "standard"
