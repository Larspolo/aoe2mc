"""Live replay on Paper: an attack ORDER shows the red order marker of the game program at its target (#845, #796):
the target unit glows, a target building gets a ring of red dust. Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
from test_replay_ai import MIL, play  # noqa: E402
from test_replay_attack import CASTLE, ENEMY  # noqa: E402
from test_replay_walk import HOUSE, VIL  # noqa: E402


def dust(sent, kind):
    return [c for c in sent if c.startswith(f"particle minecraft:dust{{color:{gather.MARK[kind]},")]


def test_an_attack_on_a_unit_makes_the_target_glow():
    _, sent, _ = play([dict(time=0, player=1, kind="order", objects=[7, 8], target=20)], (VIL, MIL, HOUSE, ENEMY))
    assert sent.count(gather.glow("e1")) == 1 and not dust(sent, "attack")


def test_an_attack_on_a_building_rings_its_footprint():
    _, sent, _ = play([dict(time=0, player=1, kind="order", objects=[8], target=21)], (MIL, HOUSE, CASTLE))
    ring = dust(sent, "attack")
    assert len(ring) == gather.MARK_POINTS and all(c.endswith(" force @a") for c in ring)
    xs = [float(c.split()[2]) for c in ring]
    zs = [float(c.split()[4]) for c in ring]
    assert min(xs) < 40 and max(xs) > 56 and min(zs) < 8 and max(zs) > 24   # around the footprint [40, 8, 56, 24)
    assert abs((min(xs) + max(xs)) / 2 - 48) < 0.5 and abs((min(zs) + max(zs)) / 2 - 16) < 0.5


def test_a_walk_order_gives_no_red_marker():
    own = dict(ENEMY, player=1)
    for e in (dict(time=0, player=1, kind="order", objects=[8], target=20),
              dict(time=0, player=1, kind="move", objects=[8], tile=[10.5, 10.5])):
        _, sent, _ = play([e], (MIL, HOUSE, own))
        assert not dust(sent, "attack") and not any("glowing" in c for c in sent)


def test_the_game_program_and_the_replay_use_the_same_marker():
    class Map:
        def y(self, x, z):
            return 70
    sent = []
    g = gather.Gather.__new__(gather.Gather)
    g.map, g.command = Map(), sent.append
    g.mark("p", {(8, 8), (11, 11)}, "attack")
    assert sent == gather.marker(Map(), {(8, 8), (11, 11)}, "attack", "p")
