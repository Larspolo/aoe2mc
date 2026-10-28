"""The axis of a straight gate comes from its center first, so a wall line beside it does not turn it (#3091)."""
import buildings


def obj(name, x, y):
    return dict(kind="B", name=name, player=1, x=x, y=y, rotation=0.0, hero=False, garrisoned=False)


def wall(x, y):
    return obj("STONE_WALL", x + 0.5, y + 0.5)


def test_parallel_wall_line_does_not_turn_a_gate_along_z():
    """A gate along tile y at (10.5, 10.0) keeps z when a wall line runs 2 or 3 tiles beside it."""
    for side in (12, 7):
        g = obj("FORTIFIED_GATE", 10.5, 10.0)
        walls, gates = buildings.plan_walls([g] + [wall(side, y) for y in range(6, 14)])
        assert gates[id(g)] is True


def test_double_wall_gates_both_go_along_z():
    """Two gate lines, at x = 10 and x = 12, with a gate in each: both gates go along z, in either order."""
    walls_at = [wall(x, y) for x in (10, 12) for y in range(6, 14) if y != 10]
    g1, g2 = obj("FORTIFIED_GATE", 10.5, 10.0), obj("FORTIFIED_GATE", 12.5, 10.0)
    for objects in ([g1, g2], [g2, g1]):
        walls, gates = buildings.plan_walls(objects + walls_at)
        assert gates[id(g1)] is True and gates[id(g2)] is True


def test_gate_along_x_keeps_its_axis():
    """A gate along tile x at (10.0, 10.5) with a parallel line 2 tiles to the south goes along x."""
    g = obj("FORTIFIED_GATE", 10.0, 10.5)
    walls, gates = buildings.plan_walls([g] + [obj("STONE_WALL", x + 0.5, 12.5) for x in range(6, 14)])
    assert gates[id(g)] is False
