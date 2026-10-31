"""up-filter-include and -exclude by the airef command, action and order ids (#5131): a gathering villager and idle
ones. The map of test_bot_gather: the bot (player 2) has a town center and five idle villagers."""
from test_per_up_filters import found
from test_per_up_search import run, script

from game import per


def setup():
    s, b, me = script()
    v = b.g.villagers[sorted(b.g.villagers)[0]]
    v.state = "chop"
    return s


def test_action_and_order_ids_keep_or_drop_the_gathering_villager():
    s = setup()
    find = "(up-find-local c: villager-class c: 20)"
    gather = per.FILTER_IDS["actionid-gather"]["id"]
    assert found(s, f"(up-filter-include -1 actionid-gather -1 -1) {find}") == (1, 0)
    run(s, "(up-reset-filters)")
    assert found(s, f"(up-filter-exclude -1 {gather} -1 -1) {find}") == (4, 0)   # by the number too
    run(s, "(up-reset-filters)")
    assert found(s, f"(up-filter-include cmdid-villager -1 orderid-gather -1) {find}") == (1, 0)
    run(s, "(up-reset-filters)")
    assert found(s, f"(up-filter-include -1 -1 orderid-build -1) {find}") == (0, 0)
    assert not s.warned


def test_an_id_with_no_state_gives_one_warning_and_is_ignored():
    s = setup()
    find = "(up-find-local c: villager-class c: 20)"
    no_state = next(r["name"] for r in per.FILTER_IDS.values() if r["kind"] == "order" and "states" not in r)
    assert found(s, f"(up-filter-include -1 -1 {no_state} -1) {find}") == (5, 0)
    assert s.warned == {("order id", no_state)}
    run(s, "(up-reset-filters) (up-filter-include -1 orderid-gather -1 -1)")   # an order id in the action place
    assert ("action id", "orderid-gather") in s.warned


def test_command_ids_of_the_game_names():
    s = setup()
    s.bot.g.soldiers["t1"] = per.FILTER_IDS["cmdid-trade"]["units"][0]
    assert found(s, "(up-filter-include cmdid-trade -1 -1 -1) (up-find-local c: villager-class c: 20)") == (0, 0)
    run(s, "(up-reset-filters)")
    assert found(s, "(up-filter-include cmdid-civilian-building -1 -1 -1) (up-find-local c: town-center c: 5)") == (1, 0)
    assert found(s, "(up-filter-include cmdid-military-building -1 -1 -1) (up-find-local c: town-center c: 5)") == (0, 0)
    assert not s.warned
