"""#3778 (epic #3774): the trigger effect "Replace Object" of buildings. The converter puts the order "replace <player>
<old> <new> <x1> <y1> <x2> <y2>" into the data storage aoe2mc:orders; the scenario mode of the game program removes
each old building with no loss and puts the complete new building on its tile (game/scenario.py replace)."""
from collections import Counter

from test_trigger_foundation import play
from test_trigger_replace import effect, lines

from game import scenario

STORED = 'Storage aoe2mc:orders has the following contents: {list: ["replace 1 HOUSE MILL 5 5 20 20"]}'


def test_a_house_by_a_mill_gives_the_order():
    stats = Counter()
    out = lines([effect(old=None, new=("B", "MILL"), player=1, area=(20, 5, 5, 20)) | {"object": ("B", "HOUSE")}], stats)
    assert out == ['data modify storage aoe2mc:orders list append value "replace 1 HOUSE MILL 5 5 20 20"']
    assert stats == Counter(replace=1)


def test_the_house_goes_and_the_complete_mill_stands_on_its_tile_with_no_loss():
    def town(stored):
        server, g, bot, _ = play('Storage aoe2mc:orders has the following contents: {list: []}')
        g.sites.append({"name": "HOUSE", "player": 1, "footprint": [9, 11, 11, 13], "done": True})
        command = server.command
        server.command = lambda cmd: stored if cmd.startswith("data get storage aoe2mc:orders") else command(cmd)
        scenario.orders(g)
        return server, g
    server, g = town(STORED)
    assert [(s["name"], s["player"], tuple(s["footprint"]), bool(s.get("done"))) for s in g.sites] == \
        [("MILL", 1, (9, 11, 11, 13), True)]
    assert not vars(g).get("buildings_lost")                         # the score and the recap count no lost building
    assert any(c.startswith("aoe destroy ") for c in server.log)
    _, g = town(STORED.replace("5 5 20 20", "0 0 3 3"))                # out of the area: the house stays
    assert [s["name"] for s in g.sites] == ["HOUSE"]
