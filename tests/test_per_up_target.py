"""The orders of an AI script to the found objects (direct unit control, #4960): up-target-objects and up-target-point
reach the paths of the game program. The map of test_bot_gather (tile size 1): the bot (player 2) has five villagers
and the soldiers of script(), player 1 (the enemy) the villager p1."""
from test_per_up_search import run, script


def commands(b, fn):
    """The commands of the game of the bot while fn runs."""
    out, cmd = [], b.g.command
    b.g.command = lambda c: out.append(c) or cmd(c)
    try:
        fn()
    finally:
        b.g.command = cmd
    return out


def test_target_objects_attacks_the_found_enemy():
    s, b, me = script()
    run(s, "(up-find-local c: infantry-class c: 20) (set-strategic-number sn-focus-player-number 1)"
           " (up-find-remote c: villager-class c: 5)")
    out = commands(b, lambda: run(s, "(up-target-objects 0 action-default -1 stance-defensive)"))
    assert "aoe attack m1 p1" in out and "aoe attack m2 p1" in out    # Gather.attack, the path of a right click
    assert "aoe stance m1 defensive" in out and not s.warned


def test_target_point_moves_patrols_and_stops():
    s, b, me = script()
    run(s, "(up-find-local c: infantry-class c: 20) (set-goal 100 10) (set-goal 101 12)")
    for u in ("m1", "m2"):                                             # the soldiers stand near the town center
        b.g.game.entities[u] = {"Pos": (24.5, 64.0, 18.5), "Rotation": (0.0, 0.0)}
    seen = []
    b.g.walk_to = lambda who, cell, units=None: seen.append((cell, sorted(units)))
    run(s, "(up-target-point 100 action-move -1 -1)")
    assert seen == [((10, 12), ["m1", "m2"])]
    out = commands(b, lambda: run(s, "(up-target-point 100 action-patrol -1 -1)"))
    assert any(c.startswith("aoe moveto @e[tag=aoe_patrol.1] 10 ") for c in out)   # stance.patrol
    assert [q[0] for q in b.g.patrols] == ["aoe_patrol.1"]
    out = commands(b, lambda: run(s, "(up-target-point 100 action-stop -1 -1)"))
    assert {"aoe stop m1", "aoe stop m2"} <= set(out)
    assert b.g.selected == set()                                       # the selection of the player stays


def test_number_tasked_units_makes_groups():
    s, b, me = script()
    s.sn["sn-number-tasked-units"] = 1
    assert s.groups(["a", "b", "c"], ["x", "y"]) == [("x", ["a"]), ("y", ["b"]), ("x", ["c"])]
    s.sn["sn-number-tasked-units"] = 0
    assert s.groups(["a", "b", "c"], ["x", "y"]) == [("x", ["a", "c"]), ("y", ["b"])]


def test_action_with_no_path_warns_once_and_the_script_goes_on(capsys):
    s, b, me = script()
    run(s, "(up-find-local c: infantry-class c: 20) (set-goal 100 10) (set-goal 101 12)"
           " (up-target-point 100 action-lock -1 -1) (up-target-point 100 action-lock -1 -1) (set-goal 5 7)")
    assert s.goals[5] == 7
    assert capsys.readouterr().err.count("action-lock") == 1
