"""game/train.py and game/gather.py: the mining camp menu has "Stone Mining" (a book, 100 food and 75 wood, 30 AoE2
seconds) next to Gold Mining. After the research a villager mines one stone in 1/1.15 of the old time, and gold does
not change (#939)."""
import pytest
from test_gold_mining import menus, setup

from game import gather, train


def test_the_mining_camp_menu_has_stone_mining():
    server, g = setup()
    train.open_menu(g, "Steve", (2, 3))
    assert menus(server)[-1].endswith(" 1:book:Stone Mining:100 food · 75 wood · 30 s · research")


def test_after_the_research_stone_is_15_percent_faster():
    server, g = setup()
    before = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    assert train.queue(g, "Steve", (3, 3), "STONE_MINING")
    assert (g.stock["food"], g.stock["wood"]) == (0, 0)
    train.tick(g, 29)
    assert g.techs == {"FEUDAL_AGE"} and g.work_time("stone") == before["stone"]
    train.tick(g, 1)
    assert g.techs == {"FEUDAL_AGE", "STONE_MINING"}
    assert g.work_time("stone") == pytest.approx(before["stone"] / 1.15)
    assert {r: g.work_time(r) for r in gather.WORK_SECONDS if r != "stone"} == \
        {r: t for r, t in before.items() if r != "stone"}                   # gold and the others stay
    assert not [c for c in server.log if c.startswith("aoe stats")]      # no combat change
    train.open_menu(g, "Steve", (3, 3))
    assert "Stone Mining" not in menus(server)[-1] and "Gold Mining" in menus(server)[-1]


def test_stone_mining_and_gold_mining_together():
    server, g = setup()
    base = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    g.techs.update({"GOLD_MINING", "STONE_MINING"})
    assert g.work_time("gold") == pytest.approx(base["gold"] / 1.15)
    assert g.work_time("stone") == pytest.approx(base["stone"] / 1.15)
    assert g.work_time("wood") == base["wood"]
