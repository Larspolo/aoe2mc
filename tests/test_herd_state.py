"""The herd tick keeps its state without hiding the method Gather.herd() (#1840): after the first tick, a right click
and the pointer of each run() call herd(), and the game stopped with "'dict' object is not callable"."""
from test_herd_capture import SHEEP, game, herd


def test_gather_herd_stays_a_method_after_the_tick():
    g, b, pos, sheep = game(sheep_owner=1)
    g.flock = {SHEEP}
    herd.tick(g)
    assert "herd" not in vars(g)
    assert g.herd() == {SHEEP}
