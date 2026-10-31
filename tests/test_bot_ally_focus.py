"""game/bot.py: an allied person asks the bot to train one class of soldiers by taunts 72 to 74 (#4886)."""
from test_bot_gather import bot_map

from game import build, train


def setup(team_of_person):
    server, me, b = bot_map()
    for p in ("1", "2"):
        b.g.players.setdefault(p, {})["team"] = team_of_person if p == "1" else 1
    b.g.data["objects"] += [{"kind": "building", "name": "BARRACKS", "player": 2, "footprint": [14, 24, 17, 27]},
                            {"kind": "building", "name": "STABLE", "player": 2, "footprint": [14, 8, 17, 11]}]
    b.g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    b.villagers = 5                                                    # no more villagers
    b.g.techs.update(build.AGE_TECHS)                                  # the stable trains its cavalry
    return server, me, b


def taunt(me, n):
    me.taunted = [*getattr(me, "taunted", []), str(n)]   # as gather.Game.clicks keeps them (#4827)


def queued(b):
    return {name for rect, name in train.homes(b.g).items() if b.g.queues.get(rect)}


def test_taunt_73_of_an_ally_trains_only_at_the_stable():
    server, me, b = setup(team_of_person=1)
    taunt(me, 73)
    b.give()
    assert b.focus == "STABLE"
    b.recruit()
    assert queued(b) == {"STABLE"}


def test_taunt_73_of_an_enemy_changes_nothing():
    server, me, b = setup(team_of_person=2)
    taunt(me, 73)
    b.give()
    assert b.focus is None
    b.recruit()
    assert queued(b) == {"BARRACKS", "STABLE"}
