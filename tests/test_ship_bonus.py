"""game/combat.py: the arrows of the towers, the castle, the town center and the dock have the AoE2 DE attack against
the class "Ships" (#1564, the "Attack bonus" field of the wiki infobox of each building). Ships have 0 armor in that
class, so the bonus adds to the pierce attack."""
from test_heated_shot import hit
from test_tower_upgrades import setup

from game import build, combat


def test_a_watch_tower_arrow_has_its_ship_bonus_and_more_after_heated_shot(monkeypatch):
    import combat as plain  # build imports combat by its plain name: a second module (#4447)
    for m in (combat, plain):   # test values (#5398)
        monkeypatch.setitem(m.BUILDINGS, "WATCH_TOWER", m.BUILDINGS["WATCH_TOWER"]._replace(attack=5, bonus={"ship": 4}))
        monkeypatch.setitem(m.STATS, "GALLEY", m.STATS["GALLEY"]._replace(pierce=2))
    _, g = setup(2)
    galley, militia, tower = combat.stats("GALLEY"), combat.stats("MILITIA"), build.values(g, "WATCH_TOWER")
    land = tower._replace(bonus={c: v for c, v in tower.bonus.items() if c != combat.SHIP})
    assert hit(tower, galley) == combat.damage("WATCH_TOWER", "GALLEY") > hit(land, galley)   # the ship bonus
    g.techs.add("HEATED_SHOT")
    assert hit(build.values(g, "WATCH_TOWER"), galley) > hit(tower, galley)
    assert hit(build.values(g, "WATCH_TOWER"), militia) == hit(tower, militia)   # not against land units
