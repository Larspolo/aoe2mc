"""The own charge attack of a unit (#4398, the Coustillier): the key "charge_attack" of data/units.jsonl sends the
plugin command of #4370 (aoe chargeattack) for each new unit. Test data, fake server of test_gather."""
from abilities import charge as ability
from test_kill_spoils import game

from game import gather, train

CHARGE = {"time": 40, "attack": 20}


def charge(monkeypatch):
    monkeypatch.setattr(ability, "UNITS", {"KNIGHT": CHARGE})


def test_a_new_unit_with_the_key_gets_its_charge(monkeypatch):
    charge(monkeypatch)
    server, g = game("FRANKS")
    u = train.summon(g, "KNIGHT", (8.5, 64.0, 8.5))
    ticks = round(CHARGE["time"] / gather.NORMAL * 20)
    assert f"aoe chargeattack {u} {ticks} {CHARGE['attack']}" in server.log


def test_a_unit_without_the_key_gets_none(monkeypatch):
    charge(monkeypatch)
    server, g = game("FRANKS")
    train.summon(g, "MILITIA", (8.5, 64.0, 8.5))
    assert not any(c.startswith("aoe chargeattack") for c in server.log)
    assert ability.command("u", "MILITIA") is None
