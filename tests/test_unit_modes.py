"""game/stance.py: a unit with a melee mode (combat.MELEE_MODE, the Ratha, #4504) gets the mode item of the stance
menu. A click switches the selected units between the ranged mode (the start) and the melee mode: aoe stats with the
values of the mode, the weapon, the range goal, and a saved game keeps the mode. Test data: a patched MELEE_MODE."""
import json

import combat as plain_combat
import pytest
from test_gather import FakeServer, grid

from game import combat, gather, savegame, stance

UNIT = "SKIRMISHER"                                                # a ranged unit of the test
MODE = {"attack": 17, "trample": {"part": 0.25, "radius": 0.5}}


@pytest.fixture(autouse=True)
def melee_mode(monkeypatch):
    for m in (combat, plain_combat):
        monkeypatch.setattr(m, "MELEE_MODE", {UNIT: MODE})


def setup():
    """A unit of UNIT ("r-1") and a militia ("k-1") of player 1, both selected, on a 40 × 40 map (tile size 1)."""
    names = {"r-1": UNIT, "k-1": "MILITIA"}
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [5.5, 5.5]} for u, n in names.items()]
    server = FakeServer({u: {"Pos": (5.5, 64.0, 5.5)} for u in names} | {"Steve": {}})
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.selected = set(names)
    return server, g


def stats(server, uuid):
    """The fields of the last aoe stats command of uuid."""
    return [c for c in server.log if c.startswith(f"aoe stats {uuid} ")][-1].split()


def click(g, server):
    stance.open_menu(g, "Steve", "r-1")
    server.log.clear()
    g.menus["Steve"]("Steve", stance.MODE, False)


def test_only_a_unit_with_a_melee_mode_has_the_mode_item():
    server, g = setup()
    assert [slot for slot, *_ in stance.items(g, "r-1") if slot == stance.MODE] == [stance.MODE]
    assert not [slot for slot, *_ in stance.items(g, "k-1") if slot == stance.MODE]


def test_a_click_switches_to_melee_and_a_second_click_back_to_ranged():
    server, g = setup()
    click(g, server)
    fields = stats(server, "r-1")
    assert fields[4] == str(MODE["attack"]) and fields[7] == "0"           # the attack of the key, range kind melee
    assert "aoe range r-1 off" in server.log
    assert not [c for c in server.log if c.startswith("aoe stats k-1 ")]  # the militia has no mode
    assert g.unit_modes == {"r-1": "melee"}
    click(g, server)
    fields = stats(server, "r-1")
    assert fields[4] == str(combat.stats(UNIT).attack) and fields[7] == "1"
    assert [c for c in server.log if c.startswith("aoe range r-1 ") and not c.endswith(" off")]
    assert g.unit_modes == {}


def test_a_load_keeps_the_melee_mode():
    server, g = setup()
    click(g, server)
    text = json.dumps(savegame.dump(g), sort_keys=True)
    hserver, h = setup()
    hserver.log.clear()
    savegame.load(h, json.loads(text))
    assert h.unit_modes == {"r-1": "melee"}
    assert stats(hserver, "r-1")[4] == str(MODE["attack"]) and "aoe range r-1 off" in hserver.log
