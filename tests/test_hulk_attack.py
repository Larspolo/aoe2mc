"""game/train.py: Forging (+1), Iron Casting (+1) and Blast Furnace (+2) give the hulk and the war hulk more attack, as
in AoE2 DE (#1509, the "Boosts" of the Hulk and War Hulk infoboxes). Fake server, no Minecraft."""
from test_forging import setup

from game import combat, train

HULK = "00000000-0000-0000-0000-0000000000cc"


def test_each_technology_gives_the_hulks_the_aoe2_attack():
    server, g = setup(food=1000)
    g.techs |= {"CASTLE_AGE", "IMPERIAL_AGE"}
    g.stock.update(gold=1000)
    g.soldiers[HULK] = "HULK"
    g.game.entities.setdefault(HULK, {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    for tech, n in (("FORGING", 1), ("IRON_CASTING", 2), ("BLAST_FURNACE", 4)):
        server.log.clear()
        assert train.order(g, "Steve", train.open_menu(g, "Steve", (11, 3)), train.ITEMS[tech][0]) == 1
        train.tick(g, train.TRAIN_TIMES[tech])
        assert tech in g.techs
        for name in train.HULKS:
            assert train.stats(g, name) == combat.stats(name)._replace(attack=combat.stats(name).attack + n)
        assert combat.stats_command(HULK, "HULK", train.stats(g, "HULK")) in server.log   # the live hulk
        for name in ("GALLEY", "FIRE_SHIP", "TRANSPORT_SHIP"):     # not the other ships
            assert train.stats(g, name) == combat.stats(name)
