"""A start age (run.py --age) does not research the switches: the policies of the Athenians and the Recruitment
Doctrines of the Macedonians change a player when it switches them, they are no technologies (#3126 review, ticket #2967)."""
import pytest
from test_gather import FakeServer, grid

from game import civs, gather, train

CIVS = [r["name"] for r in civs.ROWS]
SWITCHES = set(train.DOCTRINES) | {n for p in civs.BY_KEY["policies"].values() for n in p.get("effects", ())}


def player(civ, age, full=False):
    data = grid([[64] * 8 for _ in range(8)], [])
    data["players"] = {"1": {"civ": civ}}
    if full:
        data["full_tech_tree"] = True
    g = gather.Gather(FakeServer({}), data)
    train.start(g, age)
    return g


@pytest.mark.parametrize("full", [False, True])
@pytest.mark.parametrize("age", sorted(train.STARTS))
@pytest.mark.parametrize("civ", CIVS)
def test_a_start_age_keeps_the_switches_out_of_the_techs(civ, age, full):
    g = player(civ, age, full)
    assert not SWITCHES & g.techs


def test_athenians_keep_the_start_policy():
    g = player("ATHENIANS", "castle")
    name, _ = civs.policy(g)
    assert name == civs.policies(g)["start"]
    assert vars(g).get("switches", 0) == 0
    others = [n for n in civs.policies(g)["effects"] if n != name]
    assert others and all(train.repeatable(g, n) for n in others)


def test_macedonians_keep_the_recruitment_doctrines_offered():
    g = player("MACEDONIANS", "castle")
    assert "BARRACKS_RECRUITMENT_DOCTRINE" not in g.techs
    assert train.repeatable(g, "BARRACKS_RECRUITMENT_DOCTRINE")
