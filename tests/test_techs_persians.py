"""The unique technology of the Persians in the Imperial Age (#4281): the castle of the Persians researches Citadels,
with the values of the AoE2 DE wiki ("Unique technology"): castles +4 attack, +3 attack against rams and infantry,
and 25 % less bonus damage taken (the key "building_taken" of data/train.jsonl)."""
from test_repair import HpServer
from test_train_castle import menus, setup

from game import build, combat, gather, train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def hp_setup():
    """setup() of the Persians in the Imperial Age, with a server that keeps the hit points of the castle target: the
    castle of the map gets its new values at the research (build.retower)."""
    _, old = setup("PERSIANS", ages=3)
    server = HpServer({"Steve": {"Pos": (12.0, 64.0, 9.5), "Rotation": (180, 15)}}, {})
    g = gather.Gather(server, old.data, start={}).setup()
    g.stock.update(food=3000, wood=3000, gold=3000)
    g.techs.update(build.AGE_TECHS[:3])
    server.hp[combat.target_uuid([10, 2, 14, 6])] = combat.stats("CASTLE").hp
    return server, g


def castle_commands(server):
    """The "aoe building" commands of the castle of setup() (footprint 10, 2, 14, 6)."""
    uuid = combat.target_uuid([10, 2, 14, 6])
    return [c for c in server.log if c.startswith(f"aoe building {uuid} ")]


def test_only_the_castle_of_the_persians_researches_citadels():
    server, g = setup("PERSIANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'CITADELS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "CITADELS") is None


def test_citadels_gives_the_castle_attack_bonus_and_less_bonus_damage():
    server, g = hp_setup()
    before = build.values(g, "CASTLE")
    assert build.taken(g, "CASTLE") == 1
    assert train.queue(g, "Steve", CASTLE, "CITADELS")
    train.tick(g, train.seconds(g, "CITADELS", "CASTLE"))
    assert "CITADELS" in g.techs
    after = build.values(g, "CASTLE")
    change = train.value("effect", "CITADELS")
    assert after.attack == before.attack + change["add"]["attack"]
    for c, n in change["bonus"].items():
        assert after.bonus.get(c, 0) == before.bonus.get(c, 0) + n
    factor = train.value("building_taken", "CITADELS")["CASTLE"]
    assert build.taken(g, "CASTLE") == factor != 1
    words = castle_commands(server)[-1].split()
    assert int(words[12]) == after.attack and float(words[-1]) == factor
    assert dict(b.split(":") for b in words[-2].split(",")) == {c: str(n) for c, n in after.bonus.items()}


def test_a_castle_with_no_citadels_keeps_its_values():
    server, g = setup("PERSIANS", ages=3)
    assert "CITADELS" not in g.techs and build.taken(g, "CASTLE") == 1
    s = build.values(g, "CASTLE")
    cmd = combat.building(combat.target_uuid([10, 2, 14, 6]), "CASTLE", 1, (10, 64, 2, 13, 70, 5), s=s)[-1]
    assert int(cmd.split()[12]) == s.attack and len(cmd.split()) < 19      # no factor of the bonus damage
