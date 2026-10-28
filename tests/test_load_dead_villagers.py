"""#3109: a loaded game waits only for the start villagers that were alive at the save. A new game waits for all."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import run  # noqa: E402
import savegame  # noqa: E402


class FakeGame:
    kind, game_port, version, sides = "vanilla", 0, "26.3", {}

    def forceload(self):
        pass

    def command(self, c):
        pass


def play(tmp_path, monkeypatch, state, loads_at):
    """run.play() with two start villagers "a" and "b". The entity of "b" loads at the setup number loads_at (never if
    None). Returns (number of Gather.setup calls, seconds slept)."""
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"players": {}, "tile_size": 4, "objects": [
        {"kind": "unit", "player": 1, "name": "VILLAGER_MALE", "uuid": u, "x": 1, "y": 1} for u in ("a", "b")]}))
    setups, slept = [], []

    class FakeGather:
        bots, ended, speed = (), None, 1.0

        def __init__(self, game, data, player, **k):
            self.units = [o for o in data["objects"] if o["kind"] == "unit" and o["player"] == player
                          and "VILLAGER" in o["name"]]
            self.villagers = {}

        def setup(self):
            setups.append(self)
            for o in self.units:
                if o["uuid"] == "a" or len(setups) == loads_at:
                    self.villagers[o["uuid"]] = object()

        def run(self, seconds):
            pass

    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(run.time, "sleep", slept.append)
    monkeypatch.setattr(savegame, "load", lambda g, d: None)
    import combat
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    run.play(FakeGame(), str(tmp_path), state=state)
    return len(setups), sum(slept)


def test_a_loaded_game_does_not_wait_for_a_villager_that_died(tmp_path, monkeypatch):
    state = {"players": {"1": {"villagers": {"a": {}}}}}      # "b" was dead at the save
    assert play(tmp_path, monkeypatch, state, loads_at=None) == (1, 0)


def test_a_new_game_waits_for_a_villager_that_loads_late(tmp_path, monkeypatch):
    assert play(tmp_path, monkeypatch, None, loads_at=2) == (2, 1)
