"""game/train.py: the Feudal Age economy and blacksmith technologies show and can be researched only from the Feudal
Age, as in AoE2 DE (#1046, found by the check #965)."""
import pytest
import test_fletching
import test_forging
import test_gold_mining
import test_horse_collar

from game import train

TECHS = {"GOLD_MINING": (test_gold_mining, (2, 3)),
         "STONE_MINING": (test_gold_mining, (2, 3)),
         "HORSE_COLLAR": (test_horse_collar, (2, 3)),
         "FORGING": (test_forging, (11, 3)),
         "SCALE_MAIL_ARMOR": (test_forging, (11, 3)),
         "FLETCHING": (test_fletching, (11, 3))}


@pytest.mark.parametrize("name", TECHS)
def test_in_the_dark_age_the_menu_hides_the_technology_and_the_queue_refuses_it(name):
    (module, cell), label = TECHS[name], train.ITEMS[name][2]
    server, g = module.setup(age=0)
    g.stock.update(food=1000, wood=1000, gold=1000)
    assert train.open_menu(g, "Steve", cell) is not None
    assert f":{label}:" not in module.menus(server)[-1]
    assert train.queue(g, "Steve", cell, name) is None and not any(g.queues.values()) and g.stock["food"] == 1000


@pytest.mark.parametrize("name", TECHS)
def test_in_the_feudal_age_the_technology_shows_and_can_be_researched(name):
    (module, cell), label = TECHS[name], train.ITEMS[name][2]
    server, g = module.setup()
    g.stock.update(food=1000, wood=1000, gold=1000)
    train.open_menu(g, "Steve", cell)
    assert f":book:{label}:" in module.menus(server)[-1]
    assert train.queue(g, "Steve", cell, name) is not None
    train.tick(g, train.TRAIN_TIMES[name])
    assert name in g.techs
