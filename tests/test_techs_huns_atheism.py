"""The unique technology of the Huns in the Imperial Age (#4336): the castle of the Huns researches Atheism. The relic
and wonder victory timers of the enemies get the years of the key "rival_years" of data/train.jsonl, and their relics
give the factor "rival_relic_gold" of the gold."""
from test_relics import setup as relic_setup
from test_techs_persians import label
from test_train_castle import menus, setup

from game import monk, relic_victory, train, wonder

HOME = (14, 18, 2, 6)


def test_only_the_castle_of_the_huns_researches_atheism():
    server, g = setup("HUNS", ages=3)
    train.open_menu(g, "Steve", (12, 4))
    assert f":{label(g, 'ATHEISM')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", (12, 4))
    assert label(g, "ATHEISM") is None


def rival_with(techs):
    """relic_setup() of player 1 with a bot of player 2 (no team: an enemy) that researched techs."""
    server, g = relic_setup()
    rival = type("Bot", (), {})()
    rival.g = type("G", (), {"player": 2, "techs": set(techs), "relics": g.relics, "peers": []})()
    g.bots = [rival]
    return server, g


def test_atheism_of_an_enemy_adds_years_to_the_relic_timer_also_a_running_one():
    server, g = rival_with([])
    g.relics[0].update(at=None, home=HOME)
    full = wonder.years(g.data.get("map_size")) * wonder.YEAR
    relic_victory.tick(g, 10)
    assert g.relic_timer["left"] == full - 10
    g.bots[0].g.techs.add("ATHEISM")                                   # the research while the timer runs
    relic_victory.tick(g, 10)
    more = train.value("rival_years", "ATHEISM") * wonder.YEAR
    assert more > 0 and g.relic_timer["left"] == full + more - 20
    relic_victory.tick(g, full + more - 21)
    assert not g.ended
    relic_victory.tick(g, 1)
    assert g.ended == "Victory"


def test_own_atheism_adds_no_years():
    server, g = rival_with([])
    g.techs.add("ATHEISM")
    g.relics[0].update(at=None, home=HOME)
    relic_victory.tick(g, 0)
    assert g.relic_timer["left"] == wonder.years(g.data.get("map_size")) * wonder.YEAR


def gold(techs):
    server, g = rival_with(techs)
    g.relics[0].update(at=None, home=HOME)
    before = g.stock["gold"]
    for _ in range(60):
        monk.relic_tick(g, monk.EVERY)
    return g.stock["gold"] - before


def test_an_enemy_atheism_cuts_the_relic_gold():
    assert gold(["ATHEISM"]) == round(gold([]) * train.value("rival_relic_gold", "ATHEISM")) > 0
