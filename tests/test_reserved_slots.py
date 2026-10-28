"""Reserved menu slots (#3093): no train item takes the rally slot or a slot of the queue row."""
from game import train


def test_no_item_takes_a_slot_of_the_queue_row():
    """The queue row (ROW to MORE - 1) shows the queue, so no item of a menu takes one of its slots."""
    assert [r["name"] for r in train.ROWS if train.ROW <= r["slot"] < train.MORE] == []


def test_no_unit_or_upgrade_takes_the_rally_slot():
    """Only a building that trains units has the rally slot: a unit or an upgrade of a unit takes no such slot there."""
    rally = train.RALLY[0]
    unit_buildings = {b for b in train.TRAINS if train.units_of(b)}
    assert [r["name"] for r in train.ROWS if r["slot"] == rally and (r["building"] is None or r["building"] in unit_buildings)] == []
