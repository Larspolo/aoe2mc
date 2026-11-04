"""The trunk of a chopped tree goes to the server in one batch (#5736): after a takeover each chopped tree draws its
trunk again, and one RCON call for each probe of a slope made the game loop about 30 times too slow."""
from test_trunk_slope import FULL, World, chop, row, tree_world


class Batched(World):
    """The fake world of test_trunk_slope with Game.batch: each batch is one call."""

    def __init__(self, blocks):
        super().__init__(blocks)
        self.calls = 0

    def command(self, cmd):
        self.calls += 1
        return super().command(cmd)

    def batch(self, cmds):
        self.calls += 1
        for c in cmds:
            super().command(c)


def test_a_trunk_on_a_slope_is_one_batch_with_the_same_blocks():
    top = lambda x: 40 + x                                          # noqa: E731
    plain, g = tree_world(top)
    world, h = tree_world(top)
    world.__class__, world.calls = Batched, 0
    h.game = world
    chop(g, FULL)
    chop(h, FULL)
    assert world.blocks == plain.blocks and row(world, top) == row(plain, top)
    assert world.calls < len(plain.log) / 4                           # the probes go in batches, not one by one


def test_an_own_command_gets_each_command():
    """The crew of the replay has no game, only its own command (replay.Replay.crew)."""
    top = lambda x: 40 + x                                          # noqa: E731
    plain, g = tree_world(top)
    chop(g, FULL)
    _, h = tree_world(top)
    del h.game
    h.command = (sent := []).append
    chop(h, FULL)
    assert sent == plain.log
