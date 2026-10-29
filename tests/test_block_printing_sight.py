"""Block Printing gives the own monks more tiles of line of sight (monk.PRINTING) in the fog of war of the game
program (#1475), as in AoE2 DE ("Monk and Missionary conversion range and Line of Sight +3")."""
from test_fog_seen import T, bare, circle

from game import combat, monk, replay


def tiles(techs):
    g = bare()
    g.soldiers, g.techs = {"m": "MONK", "a": "ARCHER"}, set(techs)
    return g.seen_tiles({"m": (20.5 * T, 70.0, 20.5 * T), "a": (80.5 * T, 70.0, 20.5 * T)})


def test_the_monk_sees_its_sight_and_more_after_block_printing():
    r, more = combat.sight("MONK"), monk.PRINTING
    before, after = tiles(()), tiles({"BLOCK_PRINTING"})
    assert circle(20, 20, r) <= before and (20 + r + 1, 20) not in before and (20, 20 - r - 1) not in before
    assert circle(20, 20, r + more) <= after and (20 + r + more + 1, 20) not in after and (20 - r - more, 20) in after
    archer = {(x, y) for x, y in after if x > 50}                      # other units see as before
    assert archer == {(x, y) for x, y in before if x > 50} == circle(80, 20, combat.sight("ARCHER"))


def test_the_live_replay_keeps_the_monk_sight():
    import types
    m = types.SimpleNamespace(name="MONK", player=1, pos=(20.5 * T, 70.0, 20.5 * T))
    assert replay.seen([m], [], 1, T) == circle(20, 20, combat.sight("MONK"))
