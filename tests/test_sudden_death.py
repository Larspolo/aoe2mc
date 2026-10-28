"""#2407: `run.py --play --mode sudden-death` is the AoE2 DE game mode "Sudden Death" (wiki "Sudden Death"): each player
can have only one town center, and a player who loses it is defeated."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import build  # noqa: E402
import combat  # noqa: E402
import conquest  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402
import sudden_death  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402

TC = {1: [2, 2, 6, 6], 2: [12, 12, 16, 16]}


def game():
    """Players 1 and 2 with a town center each; player 3 has a militia and no town center."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": p, "footprint": f} for p, f in TC.items()]
    objects += [{"kind": "unit", "name": "MILITIA", "player": 3, "uuid": "m-3", "tile": [18.5, 2.5]}]
    server = FakeServer({"m-3": {"Pos": (18.5, 64.0, 2.5)}, "Steve": {}})
    g = gather.Gather(server, grid([[64] * 20 for _ in range(20)], objects)).setup()
    g.players = {str(p): {"color": "blue"} for p in (0, 1, 2, 3)}
    server.towns = {combat.target_uuid(f) for f in TC.values()}       # the target entities that stand
    command = server.command

    def answer(cmd):
        if cmd.startswith("execute if entity "):
            server.log.append(cmd)
            sel = cmd.split()[-1]
            return "Test passed, count: 1" if sel in server.towns or "aoe2mc.p1," in sel else "Test failed"
        return command(cmd)
    server.command = answer
    return server, g


def check(g):
    g.sudden_death_at = 0.0                                        # no wait of conquest.EVERY seconds
    sudden_death.tick(g)


def test_the_players_with_a_town_center_are_in_the_mode():
    server, g = game()
    sudden_death.setup(g)
    assert g.towns == {1, 2}                                       # player 3: no town center, only conquest


def test_the_loss_of_a_rival_town_center_defeats_its_player_and_wins():
    server, g = game()
    sudden_death.setup(g)
    check(g)
    assert not g.ended and not g.defeated
    server.towns.discard(combat.target_uuid(TC[2]))
    server.log.clear()
    check(g)
    assert g.defeated == {2} and "aoe destroy @e[tag=aoe2mc.building,team=p2]" in server.log
    assert any("The town center of player 2 fell" in c for c in server.log)
    g.players["3"]["team"] = g.players["1"]["team"] = 1             # player 3 is an ally: only allies are left
    conquest.tick(g)
    assert g.ended == "Victory"


def test_the_loss_of_the_own_town_center_is_a_defeat():
    server, g = game()
    sudden_death.setup(g)
    server.towns.discard(combat.target_uuid(TC[1]))
    check(g)
    assert g.ended == "Defeat"


def test_a_first_town_center_puts_a_player_into_the_mode():
    server, g = game()
    sudden_death.setup(g)
    g.sites.append({"name": "TOWN_CENTER", "player": 3, "footprint": [2, 6, 12, 16]})   # a foundation of player 3
    check(g)
    assert 3 in g.towns and not g.defeated


def test_the_build_menu_refuses_a_second_town_center_only_in_sudden_death():
    server, g = game()
    g.techs = set(build.AGE_TECHS)                                 # the Imperial Age: a second one is allowed in AoE2
    assert build.locked(g, "TOWN_CENTER") is None
    g.mode = "sudden-death"
    assert build.locked(g, "TOWN_CENTER") == "Sudden Death: only one town center"
    server.towns.discard(combat.target_uuid(TC[1]))                # no town center left: the menu does not refuse
    assert build.locked(g, "TOWN_CENTER") is None


def test_the_run_loop_checks_the_town_centers_only_in_sudden_death(monkeypatch):
    calls = []
    for m in (gather.conquest, gather.fog, gather.herd, gather.regicide, gather.sudden_death):
        monkeypatch.setattr(m, "tick", lambda g, m=m: calls.append(m.__name__))
    monkeypatch.setattr(gather.wonder, "tick", lambda g, dt: None)
    monkeypatch.setattr(gather.relic_victory, "tick", lambda g, dt: None)
    monkeypatch.setattr(gather.score, "tick", lambda g: None)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    for mode, n in (("standard", 0), ("regicide", 0), ("sudden-death", 3)):
        calls.clear()
        g = object.__new__(gather.Gather)
        g.tick, g.bots, g.ended, g.mode = 0.25, (), None, mode
        g.point = g.step = lambda: None
        g.clicks = lambda: ()
        g.run(until=lambda: calls.count("conquest") >= 3)
        assert calls.count("sudden_death") == n


def test_the_mode_option_goes_to_play(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    seen = {}
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(start=lambda: None, stop=lambda: None,
                                                                         port=0))
    monkeypatch.setattr(run, "play", lambda *a, **k: seen.update(k) or types.SimpleNamespace(ended=None))
    monkeypatch.setattr(run, "console", lambda game: None)
    run.main([str(tmp_path), "--play", "--mode", "sudden-death"])
    assert seen["mode"] == "sudden-death"


def test_play_sets_up_sudden_death(tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text('{"players": [], "tile_size": 4}')
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

        def run(self, seconds):
            seen.append(self.mode)
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(sudden_death, "setup", lambda g, m: seen.append(f"setup {m}"))
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    from test_play_speed import FakeGame
    run.play(FakeGame(), str(tmp_path), mode="sudden-death")
    assert seen == ["setup sudden-death", "sudden-death"]
