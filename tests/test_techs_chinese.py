"""Great Wall and Rocketry (#4102): the castle of the Chinese researches them with the values of the AoE2 DE wiki
("Unique technology"). Great Wall (Castle Age: 400 wood, 200 stone, 40 s): walls and towers +30% HP. Rocketry (Imperial
Age: 935 food, 765 gold, 60 s): Scorpions, Rocket Carts and Lou Chuans +25% attack. Only the Chinese have them (the key
"civ" of data/train.jsonl)."""
from test_train_castle import menus, setup

from game import build, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("GREAT_WALL", "ROCKETRY"):
        assert len(train.HELP[name]) <= 50 and "CHINESE" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_only_the_castle_of_the_chinese_researches_them():
    server, g = setup("CHINESE", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Great Wall:360 wood · 180 stone · 40 s · research " in menus(server)[-1] + " "  # 90%: the Chinese discount of the Castle Age
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Great Wall" not in menus(server)[-1]
    server, g = setup("CHINESE", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Rocketry:795 food · 650 gold · 60 s · research " in menus(server)[-1] + " "  # 85%: the Chinese discount
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Rocketry" not in menus(server)[-1]


def test_great_wall_adds_hp_to_walls_and_towers_only():
    server, g = setup("CHINESE", wood=3000, ages=2)
    g.stock.update(stone=3000)
    stone_wall = build.values(g, "STONE_WALL").hp
    guard_tower = build.values(g, "GUARD_TOWER").hp
    castle = build.values(g, "CASTLE").hp
    assert train.queue(g, "Steve", CASTLE, "GREAT_WALL")
    train.tick(g, 40)
    assert "GREAT_WALL" in g.techs
    assert build.values(g, "STONE_WALL").hp == round(stone_wall * 1.3)
    assert build.values(g, "GUARD_TOWER").hp == round(guard_tower * 1.3)
    assert build.values(g, "CASTLE").hp == castle                   # not a wall or a tower


def test_rocketry_adds_attack_to_scorpions_and_rocket_carts_only():
    server, g = setup("CHINESE", food=3000, gold=3000, ages=3)
    scorpion = train.stats(g, "SCORPION").attack
    mangonel = train.stats(g, "MANGONEL")
    assert train.queue(g, "Steve", CASTLE, "ROCKETRY")
    train.tick(g, 60)
    assert "ROCKETRY" in g.techs
    assert train.stats(g, "SCORPION").attack == round(scorpion * 1.25)
    assert train.stats(g, "MANGONEL") == mangonel                   # not a scorpion, a rocket cart or a Lou Chuan
