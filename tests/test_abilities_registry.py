"""The unit abilities are one module each in game/abilities (#4588): the package finds them, and combat.setup,
train.summon and the elite upgrade of train.research send the commands of all of them. Values from data/units.jsonl
and a test module."""
import types

import abilities
from test_kill_spoils import game

from game import combat, train


def test_each_module_has_its_key_its_type_and_its_command():
    assert abilities.MODULES and [m.__name__ for m in abilities.MODULES] == sorted(m.__name__ for m in abilities.MODULES)
    for m in abilities.MODULES:
        assert isinstance(m.KEY, str) and isinstance(m.TYPE, type) and callable(m.command), m.__name__
        assert m.UNITS == abilities.values(m.KEY), m.__name__
    assert len({m.KEY for m in abilities.MODULES}) == len(abilities.MODULES)


def test_a_unit_of_each_key_gets_the_command_of_its_ability():
    for m in abilities.MODULES:
        for name in sorted(m.UNITS):
            want = [c for x in abilities.MODULES if (c := x.command("u-1", name, 4))]
            assert abilities.commands("u-1", name, 4) == want, name
            assert m.command("u-1", name, 4) in want or m.KEY == "pack", name   # pack: no command without type tags


def test_a_unit_without_an_ability_gets_none():
    plain = next(n for n in sorted(combat.STATS) if all(n not in m.UNITS for m in abilities.MODULES))
    assert abilities.commands("u-1", plain, 4) == []


def test_a_new_module_goes_to_a_new_unit_a_start_unit_and_an_elite_unit(monkeypatch):
    test = types.SimpleNamespace(__name__="abilities.zz_test", KEY="zz_test", TYPE=dict, UNITS={},
                                 command=lambda uuid, name, T=4: f"aoe zztest {uuid} {name} {T}")
    monkeypatch.setattr(abilities, "MODULES", abilities.MODULES + [test])
    server, g = game("FRANKS")
    u = train.summon(g, "MILITIA", (8.5, 64.0, 8.5))
    assert f"aoe zztest {u} MILITIA {g.map.T}" in server.log
    tech = next(t for t in sorted(train.UPGRADES) if train.lines(t, g))
    old, new = train.lines(tech, g)[0]
    g.soldiers["e-1"] = old
    train.research(g, {"name": tech, "player": "Steve"})
    assert f"aoe zztest e-1 {new} {g.map.T}" in server.log

    class Server:
        log = []

        def command(self, c):
            self.log.append(c)
            return ""
    s = Server()
    combat.setup(s, {"objects": [{"kind": "unit", "player": 1, "uuid": "s-1", "name": "MILITIA"}], "tile_size": 4})
    assert "aoe zztest s-1 MILITIA 4" in s.log


def test_combat_and_train_have_no_function_of_one_ability():
    code = {f: open(x.__file__).read() for f, x in (("combat", combat), ("train", train))}
    for m in abilities.MODULES:
        short = m.__name__.rsplit(".", 1)[1]
        assert f"def {short}_command(uuid" not in code["combat"] and f"combat.{short}_command(" not in code["train"], short
