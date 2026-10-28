"""Many commands in one RCON round trip (#2761): `run.batches` packs them into `aoe batch` commands, the plugin runs
them in order with no feedback in the log, and the live replay sends its commands so on Paper."""
import json
import os
import shutil
import sys
import urllib.parse

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import rcon  # noqa: E402
import replay  # noqa: E402
import run  # noqa: E402


def decode(batch):
    """The commands of an `aoe batch` command, as java.net.URLDecoder reads them."""
    return [urllib.parse.unquote_plus(a) for a in batch.split(" ")[2:]]


def test_batches_keep_the_order_and_the_limit():
    cmds = [f"setblock {i} 70 3 minecraft:stone" for i in range(300)] + \
        ['tellraw @a [{"text": "50% + 1 of a b"}]', "x" * 1500, "say end"]
    out = run.batches(cmds)
    assert all(len(b.encode()) <= rcon.MAX for b in out if b != "x" * 1500)
    sent = [c for b in out for c in (decode(b) if b.startswith("aoe batch ") else [b])]
    assert sent == cmds and len(out) < len(cmds) / 10
    assert "x" * 1500 in out                                # too long for a batch: as it is
    assert run.batches(["say hi"]) == ["say hi"] and run.batches([]) == []


def test_the_replay_sends_through_the_batch_of_the_game():
    class Game:
        def __init__(self):
            self.batches, self.single = [], []

        def batch(self, cmds):
            self.batches.append(list(cmds))

        def command(self, cmd):
            self.single.append(cmd)
            return ""
    g = Game()
    r = replay.Replay(g, {"map_size": 4, "tile_size": 4, "level_height": 3, "objects": [], "players": {},
                          "ground": [" ".join(["70"] * 16)] * 16, "timeline": []})
    r.send(["say a", "say b"])
    assert g.batches == [["say a", "say b"]] and g.single == [] and r.sent == 2


@pytest.mark.mc
def test_the_plugin_runs_a_batch_in_order(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        game.command("forceload add 0 0 15 15")
        say = json.dumps([{"text": "50% + 1"}])
        cmds = ["setblock 2 200 2 minecraft:stone", "setblock 2 200 2 minecraft:gold_block",     # the order counts
                "execute if block 2 200 2 minecraft:gold_block run setblock 3 200 2 minecraft:oak_stairs[facing=east]",
                f"tellraw @a {say}", 'summon minecraft:zombie 2.5 201 2.5 {NoAI:1b,Tags:["batch"]}', "aoe stop @e[tag=batch]"]
        out = run.batches(cmds)
        assert len(out) == 1
        assert game.command(out[0]).strip() == f"Batch: {len(cmds)}/{len(cmds)}"
        for test in ("block 2 200 2 minecraft:gold_block", "block 3 200 2 minecraft:oak_stairs[facing=east]",
                     "entity @e[tag=batch]"):
            assert "passed" in game.command(f"execute if {test}"), test
        log = open(game.folder + "/logs/latest.log").read()
        assert "Changed the block" not in log and "50% + 1" not in log      # no feedback lines in the log
