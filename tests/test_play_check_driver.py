"""tools/play_check.py: the driver plays player 1 as a person (#3544): the bell, the saving for an age, the minute line."""
import play_check
from test_bot_gather import bot_map
from test_play_check import ready


def raid(foes, monkeypatch):
    """Two own militia and this many foe militia near the town center of player 1; the driver defends and rings."""
    server, me, b = bot_map()
    monkeypatch.setattr(play_check.garrison, "order", lambda g, player, cell: (2, 6, 2, 6))   # the fake has no plugin
    d = play_check.Driver(me, b.g)
    for i in range(2):
        me.soldiers[f"s{i}"] = "MILITIA"
        server.entities[f"s{i}"] = {"Pos": (7.5, 64.0, 7.5 + i)}
    for i in range(foes):
        b.g.soldiers[f"f{i}"] = "MILITIA"
        server.entities[f"f{i}"] = {"Pos": (9.5, 64.0, 8.5 + i)}
    d.defend()
    d.bell()
    return d


def test_the_bell_rings_only_when_the_foes_are_more_than_the_own_soldiers(monkeypatch):
    d = raid(1, monkeypatch)
    assert len(d.foes) == 1 and d.guards == 2 and not d.rung
    d = raid(3, monkeypatch)
    assert len(d.foes) == 3 and d.rung


def test_the_driver_keeps_saving_for_the_age_when_a_villager_dies():
    server, me, b = bot_map()
    d = play_check.Driver(me, b.g)
    ready(me)
    me.stock.update(food=370, wood=0, gold=0, stone=0)
    d.advance()
    assert d.saving == "FEUDAL_AGE"
    me.villagers.pop(sorted(me.villagers)[-1])                         # 20 → 19
    d.advance()
    assert d.saving == "FEUDAL_AGE"
    d.recruit()
    assert not any(me.queues.values()) and me.stock["food"] == 370


def test_the_minute_line_names_the_stock_and_the_villager_states(capsys):
    server, me, b = bot_map()
    d = play_check.Driver(me, b.g)
    me.stock.update(food=120, wood=55, gold=0, stone=0)
    w = play_check.Watch(me, [d])
    w.shown = -60
    w.step()
    line = capsys.readouterr().err
    assert "stock food 120" in line and "wood 55" in line and "idle/wood 1" in line
