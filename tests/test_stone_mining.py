"""game/train.py and game/gather.py: the mining camp researches "Stone Mining" next to Gold Mining. After the research
a villager mines stone faster, and gold does not change (#939)."""
from test_gold_mining import menus, setup

from game import gather, train


def test_after_the_research_stone_is_faster():
    server, g = setup()
    before = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    stock, t = dict(g.stock), train.TRAIN_TIMES["STONE_MINING"]
    assert train.queue(g, "Steve", (3, 3), "STONE_MINING")
    assert all(g.stock[r] == stock[r] - v for r, v in train.COSTS["STONE_MINING"].items())
    train.tick(g, t - 1)
    assert g.techs == {"FEUDAL_AGE"} and g.work_time("stone") == before["stone"]
    train.tick(g, 1)
    assert g.techs == {"FEUDAL_AGE", "STONE_MINING"}
    assert g.work_time("stone") < before["stone"]
    assert {r: g.work_time(r) for r in gather.WORK_SECONDS if r != "stone"} == \
        {r: t for r, t in before.items() if r != "stone"}                   # gold and the others stay
    assert not [c for c in server.log if c.startswith("aoe stats")]      # no combat change
    train.open_menu(g, "Steve", (3, 3))
    label = train.slots("MINING_CAMP", "STONE_MINING")[2]
    assert f":{label}:" not in menus(server)[-1] and f":{train.slots('MINING_CAMP', 'GOLD_MINING')[2]}:" in menus(server)[-1]


def test_stone_mining_and_gold_mining_together():
    server, g = setup()
    base = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    g.techs.add("GOLD_MINING")
    gold = g.work_time("gold")
    g.techs.add("STONE_MINING")
    assert g.work_time("gold") == gold < base["gold"]
    assert g.work_time("stone") < base["stone"]
    assert g.work_time("wood") == base["wood"]
