"""The built-in XS constants (game/data/xs_constants.jsonl) and the population attributes of xsPlayerAttribute (#5807)."""
from game import table, xs_host
from game.xs_run import Xs
from tests.test_xs_host import side

ROWS = {r["name"]: r for r in table.load("xs_constants.jsonl")}


def run(g, name):
    x = Xs(f"void main() {{ xsSetTriggerVariable(10, xsPlayerAttribute(1, {name})); }}", host=xs_host.host(g))
    x.tick(0)
    return g.scores["#v10"]


def test_population_attributes_count_the_units_of_the_side(capsys):
    g = side()
    g.soldiers = {f"u{i}": "ARCHER" for i in range(3)}
    g.units = [{"name": "VILLAGER_MALE"}] * 4
    assert run(g, "cAttributeMilitaryPopulation") == 3
    assert run(g, "cAttributePopulation") == 7
    assert run(g, "cAttributeCivilianPopulation") == 4
    assert run(g, "cAttributeFood") == g.stock["food"]
    assert "unknown" not in capsys.readouterr().err


def test_each_constant_is_a_const_global_of_its_value():
    x = Xs("")
    for name, r in ROWS.items():
        typ = next(k for k in r if k != "name")
        assert x.globals[name][0] == typ and x.globals[name][2], name
        assert x.get(name) == (tuple(r[typ]) if typ == "vector" else r[typ]), name


def test_a_script_constant_replaces_the_built_in_one():
    name = next(iter(ROWS))
    assert Xs(f"const int {name} = 12345;").get(name) == 12345
