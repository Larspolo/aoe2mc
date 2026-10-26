"""game/build.py: the ghost of the chosen building follows the look of the player (#794). Fake server; an mc test on
Paper with the plugin (Ghost.java)."""
import json
import shutil

import pytest
from test_build_site import Server, site_map

from game import build


def cube(n):
    return {(x, y, z): "stone" for x in range(n) for y in range(n) for z in range(n)}


def test_the_shape_keeps_the_outer_blocks():
    parts, k = build.shape(cube(3))
    assert k == 1 and len(parts) == 26 and (1, 1, 1) not in parts
    parts, k = build.shape(cube(8), limit=100)                         # 296 outer blocks: cells of 2 × 2 × 2
    assert k == 2 and len(parts) == 56 and set(parts.values()) == {"stone"}


class Look(Server):
    def command(self, cmd):
        if cmd == "execute if entity @a[scores={aoe_build=1..}]":
            self.log.append(cmd)
            return "Test passed. Count: 1" if self.chosen else "Test failed"
        return super().command(cmd)


def ghost(chosen=1):
    server, g = site_map()
    server.__class__ = Look
    server.chosen, g.paper = chosen, True
    return server, g


def test_a_chosen_house_shows_its_ghost_once_and_green():
    server, g = ghost()
    server.log.clear()
    build.tick(g)
    shape = [c for c in server.log if c.startswith("aoe ghost")]
    assert shape[0] == "aoe ghost-clear Steve" and shape[-2:] == ["aoe ghost Steve 1 2", "aoe ghost-color Steve green"]
    parts = [t for c in shape if c.startswith("aoe ghost-shape Steve 1 ") for t in c.split()[4:]]
    assert parts and all(len(c) <= 1446 for c in shape)
    assert min(int(t.split("/")[1]) for t in parts) == -1              # the floor; no foundation under it
    assert not any("/air" in t or "/barrier" in t for t in parts)
    server.log.clear()
    build.tick(g)
    assert not any(c.startswith("aoe ghost") for c in server.log)      # the same look: nothing new


def test_the_ghost_is_red_over_a_blocked_footprint_and_goes_away_after_the_choice():
    server, g = ghost()
    build.tick(g)
    server.entities["Steve"]["Rotation"] = (0.0, 90.0)                 # straight down: the cell under Steve
    g.map.blocked.add((8, 12))
    server.log.clear()
    build.tick(g)
    assert [c for c in server.log if c.startswith("aoe ghost")] == ["aoe ghost-color Steve red"]
    server.chosen = 0
    server.log.clear()
    build.tick(g)
    assert [c for c in server.log if c.startswith("aoe ghost")] == ["aoe ghost-clear Steve"] and not g.ghosts


def test_no_ghost_without_the_plugin():
    server, g = ghost()
    g.paper = False
    build.tick(g)
    assert not any(c.startswith("aoe ghost") for c in server.log)


@pytest.mark.mc
def test_the_ghost_commands_work_on_paper(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import gather, run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    data = json.load(open(world / "aoe2mc.json"))
    with run.Game(world) as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        game.command("summon minecraft:armor_stand 8 80 8 {NoGravity:1b}")   # a stand-in for a player: no client here
        x0, z0 = 4 * g.map.T, 4 * g.map.T
        cmds = build.ghost_commands(g, "@e[type=armor_stand,limit=1]", "HOUSE", (x0, x0 + 2 * g.map.T, z0, z0 + 2 * g.map.T))
        answers = [game.command(c) for c in cmds]
        assert all(a.startswith("Ghost:") for a in answers), answers   # the selector is no player: "Ghost: 0"
        assert len(g.shapes["HOUSE"][0]) > 20
