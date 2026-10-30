"""game/gather.py: a control group item says how to use it (#1812): the save click when empty, the select click and the
number of units when saved."""
from test_control_groups import use
from test_select_type import setup

from game import gather


def item(log, n):
    """The last item replace of the hotbar slot of group n in the log."""
    slot = gather.GROUPS[n][0]
    return [c for c in log if "item replace" in c and f"hotbar.{slot} " in c][-1]


def test_an_empty_group_item_names_the_save_click():
    i = gather.group_item(2)
    assert 'item_name="Group 2 (empty)"' in i and 'lore=["Shift + right click: save the selection"]' in i
    assert "custom_data={aoe_group:2}" in i


def test_a_saved_group_item_names_the_select_click_and_its_units():
    i = gather.group_item(3, 4)
    assert 'item_name="Group 3: 4 units"' in i and "custom_data={aoe_group:3}" in i
    assert 'lore=["Right click: select · Shift + right click: save again"]' in i
    assert 'item_name="Group 1: 1 unit"' in gather.group_item(1, 1)


def test_a_save_renames_the_item_and_a_select_follows_a_dead_unit():
    server, g = setup()
    g.choose({"m-1", "m-2"})
    log = use(server, g, 1, sneak=True)
    assert 'item_name="Group 1: 2 units"' in item(log, 1) and item(log, 1).split()[3] == "Steve"
    server.log.clear()
    del server.entities["m-2"]
    log = use(server, g, 1)
    assert 'item_name="Group 1: 1 unit"' in item(log, 1)
    server.log.clear()
    g.choose(set())
    log = use(server, g, 1, sneak=True)                                 # an empty selection empties the group
    assert 'item_name="Group 1 (empty)"' in item(log, 1)


def test_the_give_of_a_missing_item_has_the_saved_units():
    server, g = setup()
    g.groups[5] = {"m-1", "a-1", "v-1"}
    server.log.clear()
    g.calls = 0
    g.clicks()
    give = [c for c in server.log if "unless items" in c and "aoe_group:5}]" in c and "item replace" in c]
    assert give and 'item_name="Group 5: 3 units"' in give[0]
