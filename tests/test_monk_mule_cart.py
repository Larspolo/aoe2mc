"""game/monk.py: a monk does not heal a mule cart. AoE2 DE wiki "Mule Cart": "The Mule Cart is considered a building
which can move and not a unit" (#2522); villagers repair it (#2504), a garrison repairs it (#2505)."""
import pytest
from test_monk_heal import run, setup

from game import monk


def test_a_monk_heals_a_militia_but_not_a_mule_cart():
    server, g = setup(("cart", "MULE_CART", 1, 6.5, 30.0, 300.0), ("a", "MILITIA", 1, 7.5, 10.0, 40.0))
    g.soldiers.update(cart="MULE_CART")
    run(g, 4)
    assert server.entities["cart"]["Health"] == 30.0
    assert server.entities["a"]["Health"] == pytest.approx(10 + 4 * 2.5)
    assert not monk.healable("MULE_CART") and monk.healable("MILITIA")
