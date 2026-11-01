"""#5537: a player in the camera mode sees the amounts left large; the other players see the normal display."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import amounts  # noqa: E402
import camera  # noqa: E402
import gather  # noqa: E402

KEY = ("trees", (2, 3))
BIG, NORMAL = amounts.uid(KEY, amounts.BIG), amounts.uid(KEY)


def side():
    m = types.SimpleNamespace(T=4, n=8, trees={(2, 3): gather.TREE_WOOD - 5}, bushes={}, mines={}, farms={},
                              carcasses={}, farm_food=175, y=lambda x, z: 10, ground=[[10]])
    log = []
    g = types.SimpleNamespace(map=m, data={"objects": []}, paper=True, camera_on={"Cam"},
                              command=lambda c: log.append(c) or "")
    return g, log


def test_a_new_display_is_large_only_for_the_camera_player():
    g, log = side()
    amounts.tick(g)
    big = next(c for c in log if amounts.BIG in c and c.startswith("summon"))
    assert "scale:[4f,4f,4f]" in big and BIG.split("-")[0] not in big     # UUID as ints
    assert log[-3:] == [f"aoe hide @a view {BIG}", f"aoe show Cam view {BIG}", f"aoe hide Cam view {NORMAL}"]
    assert not any("Alex" in c for c in log)                            # Alex sees the normal one, not the large one


def test_a_switch_swaps_the_displays_of_the_player():
    g, log = side()
    g.camera_on = set()
    amounts.tick(g)
    log.clear()
    g.command = lambda c: log.append(c) or ""
    camera.click(g, "Alex")                                            # on: "Camera: on" is not in the answer
    assert f"aoe show Alex view {BIG}" in log and f"aoe hide Alex view {NORMAL}" in log
    assert g.camera_on == {"Alex"}
    log.clear()
    g.command = lambda c: log.append(c) or ("Camera: on" if c == "aoe camera Alex" else "")
    camera.click(g, "Alex")                                            # off
    assert f"aoe hide Alex view {BIG}" in log and f"aoe show Alex view {NORMAL}" in log
    assert g.camera_on == set()


def test_a_vanilla_world_has_only_the_normal_display():
    g, log = side()
    g.paper = False
    amounts.tick(g)
    assert not any(amounts.BIG in c or c.startswith("aoe ") for c in log)
