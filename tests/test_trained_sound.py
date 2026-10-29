"""The unit that an own building completes plays its select voice to the team of its player (AoE2 DE, #3563). A
technology plays no unit voice. Fake server, no Minecraft."""
from test_loom import setup as loom
from test_train import setup as town
from test_train_barracks import setup as barracks

from game import train


def voices(server):
    return [c for c in server.log if c.startswith("playsound") and " voice " in c]


def test_a_town_center_that_completes_a_villager_plays_the_villager_voice_to_the_team():
    server, g = town()
    g.player = 1                                                     # the own player number, as in a game
    train.queue(g, "Steve", (3, 3))
    train.tick(g, train.TRAIN_TIMES["VILLAGER_MALE"])
    assert voices(server) == ["playsound minecraft:entity.villager.yes voice @a[team=p1] 3.5 64 3.5 1 1.0"]


def test_a_barracks_that_completes_a_militia_plays_the_infantry_voice_to_the_team():
    server, g = barracks()
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, 0)
    train.tick(g, train.TRAIN_TIMES["MILITIA"])
    assert len(voices(server)) == 1 and voices(server)[0].startswith("playsound minecraft:item.armor.equip_iron voice @a[team=p1] ")


def test_a_complete_technology_sends_no_unit_voice():
    server, g = loom(food=1000, gold=1000)
    train.research(g, {"name": "LOOM", "player": 1})
    assert voices(server) == []
