"""Block Printing gives the own monks +3 tiles of line of sight in the fog of war of the game program (#1475), as in
AoE2 DE ("Monk and Missionary conversion range and Line of Sight +3"). The monk sees 11 tiles (wiki infobox "LOS")."""
from test_fog_seen import T, bare, circle

from game import combat, monk, replay


def tiles(techs):
    g = bare()
    g.soldiers, g.techs = {"m": "MONK", "a": "ARCHER"}, set(techs)
    return g.seen_tiles({"m": (20.5 * T, 70.0, 20.5 * T), "a": (80.5 * T, 70.0, 20.5 * T)})


def test_the_monk_sees_11_tiles_and_3_more_after_block_printing():
    assert combat.sight("MONK") == 11 and monk.PRINTING == 3
    before, after = tiles(()), tiles({"BLOCK_PRINTING"})
    assert circle(20, 20, 11) <= before and (20 + 12, 20) not in before and (20, 20 - 12) not in before
    assert circle(20, 20, 14) <= after and (20 + 15, 20) not in after and (20 - 14, 20) in after
    archer = {(x, y) for x, y in after if x > 50}                      # other units see as before
    assert archer == {(x, y) for x, y in before if x > 50} == circle(80, 20, combat.sight("ARCHER"))


def test_the_live_replay_keeps_the_monk_sight():
    import types
    m = types.SimpleNamespace(name="MONK", player=1, pos=(20.5 * T, 70.0, 20.5 * T))
    assert replay.seen([m], [], 1, T) == circle(20, 20, 11)
