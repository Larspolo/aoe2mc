"""The click of tools/takeover_check.py on "Villager" (#5812): the unit item of the town center menu, not the queue row.
With a queue, train.show puts the queue row first, with the same names, and a click there cancels a unit."""
import takeover_check
import train


def menu(queued):
    """The items of a town center menu as train.show gives them: the queue row (queued groups) first."""
    row = [(train.ROW + i, "villager_spawn_egg", "Villager" + (" 49 %" if i == 0 else ""), "Click: cancel 1", 5)
           for i in range(queued)]
    return row + [(0, "villager_spawn_egg", "Villager", "50 food · 25 s · queue 9/15"),
                  (1, "book", "Loom", "50 gold · 25 s · research"), train.RALLY]


def test_the_click_takes_the_unit_item_also_with_a_queue():
    assert takeover_check.unit_slot(menu(0)) == 0
    assert takeover_check.unit_slot(menu(2)) == 0
    assert takeover_check.unit_slot(menu(2), "Loom") == 1


def test_no_unit_item_gives_no_slot():
    assert takeover_check.unit_slot(menu(2)[:2]) is None


def test_a_cancel_fails_the_point_and_shows_the_chat():
    one = {"time": 0.0, "stock": {"food": 200, "gold": 100, "stone": 200, "wood": 100}, "pop": 6, "villagers": 5,
           "idle": 0, "idle_jobs": [], "soldiers": [], "queued": 9, "age": [], "bot_sites": {"2": 3}}
    last = one | {"villagers": 7}
    saved = {"stock": one["stock"], "techs": []}
    ok, detail = takeover_check.result(saved, one, last, 0, [], said=["Not enough resources"])["the town center trains"]
    assert not ok and "Not enough resources" in detail
    assert takeover_check.result(saved, one, last, 1, [])["the town center trains"][0]
