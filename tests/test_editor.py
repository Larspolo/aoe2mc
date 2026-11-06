"""game/run.py --editor (#5999): the map editor starts no game, and `save` exports the world to the scenario file."""
import contextlib
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
import export  # noqa: E402
import run  # noqa: E402
import world_reader  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402
from test_export_terrain import set_blocks, surface  # noqa: E402


class Server:
    def __init__(self, log):
        self.log = log


class FakeGame:
    """run.Game without a server: it records the commands."""
    def __init__(self, world, *a, **k):
        self.world, self.sent, self.server = world, [], Server([])
        self.rcon, self.port = object(), 0

    def start(self):
        return self

    def command(self, cmd):
        self.sent.append(cmd)
        return ""

    def stop(self):
        pass


def test_editor_starts_no_game_and_saves_at_the_stop(tiny_world, tmp_path, monkeypatch):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    games, exported = [], []
    monkeypatch.setattr(run, "Game", lambda *a, **k: games.append(FakeGame(*a)) or games[-1])
    monkeypatch.setattr(run, "ctrl_c", lambda: None)
    monkeypatch.setattr(run, "play", lambda *a, **k: (_ for _ in ()).throw(AssertionError("play() runs")))
    monkeypatch.setattr(run, "console", lambda game: type("T", (), {"is_alive": lambda self: False})())
    monkeypatch.setattr(export, "export", lambda folder, out: exported.append((folder, out)) or out)
    out = str(tmp_path / "out.aoe2scenario")
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        run.main([world, "--editor", out])
    (folder, got), = exported
    assert got == out and os.path.isdir(os.path.join(folder, "world"))
    assert getattr(games[0], "g", None) is None                     # no Gather: no gather tick, bot or victory


def test_the_chat_word_save_counts_only_save_lines():
    game = FakeGame("w")
    game.server.log = ["[12:00:00 INFO]: <Steve> save", "[12:00:01 INFO]: <Steve> saved it",
                       "[12:00:02 INFO]: [Not Secure] <Alex> save"]
    assert editor.words(game, 0) == (3, 2)
    assert editor.words(game, 3) == (3, 0)


def test_a_painted_tile_has_its_terrain_in_the_saved_map(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    T, n = data["tile_size"], data["map_size"]
    terrain = [[int(v) for v in r.split()] for r in data["terrain"]]
    tops, of, loose = export.terrain_tops()
    feet = {(x, y) for o in data["objects"] if "footprint" in o
            for x in range(o["footprint"][0] // T, -(-o["footprint"][2] // T))
            for y in range(o["footprint"][1] // T, -(-o["footprint"][3] // T))}
    tx, ty = next((x, y) for y in range(n // 2, n) for x in range(n)
                  if (x, y) not in feet and of[terrain[y][x]] == "grass_block")
    new = next(b for b in tops if b not in ("grass_block", "farmland"))
    w = world_reader.World(world)
    set_blocks(world, {(X, surface(w, X, Z), Z): new for X in range(tx * T, tx * T + T) for Z in range(ty * T, ty * T + T)})
    game = FakeGame(world)
    out = str(tmp_path / "out.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(game, out)
        scn = AoE2DEScenario.from_file(out)
    got = {(t.x, t.y): t.terrain_id for t in scn.map_manager.terrain}
    assert got[(tx, ty)] == tops[new]
    assert "save-all flush" in game.sent and any("aoe2mc.editor.saved" in c for c in game.sent)
