"""#2440: `run.py --play --mode capture-the-relic` is the AoE2 DE game mode "Capture the Relic" (wiki "Capture the
Relic"): one relic lies at the map center, and the first player who brings it into an own monastery wins at once."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import capture_relic  # noqa: E402
import combat  # noqa: E402
import gather  # noqa: E402
import monk  # noqa: E402
import run  # noqa: E402
from test_relics import setup  # noqa: E402

HOME = (14, 18, 2, 6)                                                  # the own monastery of test_relics (a rect)


def start():
    server, g = setup()
    g.players = {str(p): {"color": "blue"} for p in (0, 1, 2)}
    server.log.clear()
    capture_relic.setup(g)
    return server, g


def test_the_relic_lies_at_the_map_center():
    server, g = start()
    assert g.relics[-1] == {"at": (12, 12), "monk": None, "home": None, "center": True}
    assert len([r for r in g.relics if r.get("center")]) == 1
    assert f"setblock 12 64 12 {monk.POT} keep" in server.log


def test_a_building_at_the_center_moves_the_relic_to_the_nearest_free_cell():
    server, g = setup()
    g.map.blocked |= {(x, z) for x in range(10, 15) for z in range(10, 15)}
    capture_relic.setup(g)
    assert g.relics[-1]["at"] == (9, 12)                              # the first of the cells 3 blocks away


def test_the_center_relic_in_an_own_monastery_wins_at_once():
    server, g = start()
    capture_relic.tick(g)
    assert not g.ended
    g.relics[-1].update(at=None, home=HOME)
    capture_relic.tick(g)
    assert g.ended == "Victory" and 'title @a[team=p1] title {"translate":"aoe2mc.victory","fallback":"Victory","color":"gold"}' in server.log


def test_another_relic_in_a_monastery_does_not_win():
    server, g = start()
    g.relics[0].update(at=None, home=HOME)                             # the relic of the scenario
    capture_relic.tick(g)
    assert not g.ended


def test_the_center_relic_of_a_rival_is_a_defeat(monkeypatch):
    server, g = start()
    rival = types.SimpleNamespace(g=types.SimpleNamespace(player=2, relics=[{**g.relics[-1], "home": HOME}],
                                                          ended=None))
    g.bots = [rival]
    monasteries = monk.monasteries
    monkeypatch.setattr(monk, "monasteries", lambda h: {HOME} if h is rival.g else monasteries(h))
    capture_relic.tick(g)
    assert g.ended == "Defeat" and rival.g.ended == "Victory"
    assert 'title @a[team=p1] title {"translate":"aoe2mc.defeat","fallback":"Defeat","color":"red"}' in server.log


def test_the_run_loop_checks_the_relic_only_in_capture_the_relic(monkeypatch):
    calls = []
    for m in (gather.conquest, gather.fog, gather.herd, gather.regicide, gather.sudden_death, gather.capture_relic):
        monkeypatch.setattr(m, "tick", lambda g, m=m: calls.append(m.__name__))
    for m in (gather.wonder, gather.relic_victory, gather.treaty):
        monkeypatch.setattr(m, "tick", lambda g, dt: None)
    monkeypatch.setattr(gather.score, "tick", lambda g: None)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    for mode, n in (("standard", 0), ("sudden-death", 0), ("capture-the-relic", 3)):
        calls.clear()
        g = object.__new__(gather.Gather)
        g.tick, g.bots, g.ended, g.mode = 0.25, (), None, mode
        g.point = g.step = lambda: None
        g.clicks = lambda: ()
        g.run(until=lambda: calls.count("conquest") >= 3)
        assert calls.count("capture_relic") == n


def test_the_mode_option_goes_to_play(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    seen = {}
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(start=lambda: None, stop=lambda: None,
                                                                         port=0))
    monkeypatch.setattr(run, "play", lambda *a, **k: seen.update(k) or types.SimpleNamespace(ended=None))
    monkeypatch.setattr(run, "console", lambda game: None)
    run.main([str(tmp_path), "--play", "--mode", "capture-the-relic"])
    assert seen["mode"] == "capture-the-relic"


def test_play_puts_the_relic_only_in_a_new_capture_the_relic_game(tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text('{"players": [], "tile_size": 4}')
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed, mode = (), [], [], None, 1.0, "standard"

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

        def run(self, seconds):
            seen.append(self.mode)
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(capture_relic, "setup", lambda g, m: seen.append(f"setup {m}"))
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    import savegame
    monkeypatch.setattr(savegame, "load", lambda g, state: None)
    from test_play_speed import FakeGame
    run.play(FakeGame(), str(tmp_path), mode="capture-the-relic")
    assert seen == ["setup capture-the-relic", "capture-the-relic"]
    seen.clear()
    run.play(FakeGame(), str(tmp_path), mode="standard")
    assert seen == ["standard"]                                        # the standard mode has no extra relic
    seen.clear()
    run.play(FakeGame(), str(tmp_path), mode="capture-the-relic", state={"players": {}})
    assert seen == ["capture-the-relic"]                               # a loaded game: the relic is in the save
