"""game/per.py: an AI script keeps resources apart with escrow (#4682). The map of test_bot_gather."""
from test_bot_gather import bot_map
from test_per_save import scripted
from test_savegame_bots import game

from game import per, savegame
from game.bot import train                                             # the module that per uses


def script(text):
    server, me, b = bot_map()
    return per.Script(per.parse(text), b), b


def test_half_of_new_food_goes_into_escrow():
    s, b = script("(defrule (true) => (set-escrow-percentage food 50) (disable-self))")
    price = train.price(b.g, "VILLAGER_MALE")["food"]
    b.g.stock["food"] = 0
    s.step()                                                           # the stock now: no new income
    b.g.stock["food"] = 2 * price
    s.step()
    assert s.escrow["food"] == price and s.check(("escrow-amount", "food", "==", price))
    b.g.stock["food"] = 2 * price - 1                                  # only the escrow pays the last food
    assert not s.check(("can-train", "villager")) and s.check(("can-train-with-escrow", "villager"))


def test_train_does_not_spend_the_escrow_until_release():
    s, b = script("(defrule (true) => (train villager))\n(defrule (goal 1 1) => (release-escrow food))")
    s.escrow["food"] = b.g.stock["food"] = train.price(b.g, "VILLAGER_MALE")["food"]
    s.last = dict(b.g.stock)
    s.step()
    assert b.g.stock["food"] == s.escrow["food"] and not any(b.g.queues.values())
    s.goals[1] = 1
    s.step()                                                           # the release runs after the train of this step
    assert "food" not in s.escrow and s.check(("can-train", "villager"))


def test_a_load_keeps_the_escrow():
    me = scripted(game(("standard",) * 3, (1, 1, 1)))
    s = me.bots[0].script
    s.escrow, s.pct, s.last = {"food": 30}, {"food": 50}, {"food": 30}
    new = scripted(game(("standard",) * 3, (1, 1, 1)))
    savegame.load(new, savegame.dump(me))
    t = new.bots[0].script
    assert (t.escrow, t.pct, t.last) == (s.escrow, s.pct, s.last)
