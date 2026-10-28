"""game/monk.py: the relics of a fallen monastery lie each on its own cell, with its own pot (#3010). Fake server."""
from test_relics import setup

from game import monk

FALLEN = (4, 8, 4, 8)                                                  # block footprint of a monastery that fell


def test_each_relic_of_a_fallen_monastery_gets_its_own_cell():
    server, g = setup()
    g.relics = [{"at": None, "monk": None, "home": FALLEN}, {"at": None, "monk": None, "home": FALLEN}]
    monk.relic_tick(g, monk.EVERY)
    cells = [r["at"] for r in g.relics]
    assert None not in cells and len(set(cells)) == 2
    for x, z in cells:
        assert f"setblock {x} 64 {z} minecraft:decorated_pot keep" in server.log
    assert all(monk.order(g, "Steve", cell) for cell in cells)            # an own monk takes each relic again
