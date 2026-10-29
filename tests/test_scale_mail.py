"""game/train.py: the blacksmith menu has "Scale Mail Armor". A click queues it once and takes its cost; after the
research the new units of the player have it too (#725)."""
from test_forging import menus, setup

from game import combat, train

NAME = "SCALE_MAIL_ARMOR"


def test_a_click_queues_scale_mail_armor_once_and_takes_its_cost():
    server, g = setup(food=1000)
    slot, item, label = train.slots("BLACKSMITH", NAME)
    rect = train.open_menu(g, "Steve", (11, 3))
    food = 1000 - train.COSTS[NAME]["food"]
    assert train.order(g, "Steve", rect, slot, shift=True) == 1 and g.stock["food"] == food
    assert train.order(g, "Steve", rect, slot) == 0 and g.stock["food"] == food
    assert (menus(server)[-1] + " ").split(f" {slot}:{item}:{label}:", 1)[1].split(" · ")[2].startswith("researching ")


def test_a_new_militia_has_the_scale_mail_armor():
    server, g = setup()
    g.stock.update(train.COSTS["MILITIA"])
    g.techs.add(NAME)
    assert train.queue(g, "Steve", (17, 3), "MILITIA")
    uuid, = train.tick(g, train.TRAIN_TIMES["MILITIA"])
    assert combat.stats_command(uuid, "MILITIA", train.stats(g, "MILITIA")) in server.log
