"""The cheat code "polo" removes the fog of war of the game program and a second "polo" puts it back (#1390)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import cheats  # noqa: E402
import fog  # noqa: E402
import lang  # noqa: E402
from test_fog_units import E1, E2, at, bare  # noqa: E402


def test_polo_shows_the_hidden_enemies_and_stops_the_fog():
    g = bare()
    g.reveal = "normal"
    g.where = lambda want: {"v": at(10, 10), E1: at(60, 10), E2: at(60, 12)}
    fog.tick(g)
    assert g.sent == [f"aoe hide @a[team=p1] {E1} {E2}"]
    cheats.apply(g, "Steve", "polo")
    assert [*map(lang.english, g.sent[1:])] == [f"aoe show @a[team=p1] {E1} {E2}", 'tellraw Steve "Fog of war: off"']
    assert g.reveal == "all" and g.fog["hidden"] == set()
    g.now = 5.0
    fog.tick(g)
    assert len(g.sent) == 3                                         # no fog update


def test_a_second_polo_puts_the_fog_back_at_once():
    g = bare()
    g.reveal = "normal"
    g.where = lambda want: {"v": at(10, 10), E1: at(60, 10)}
    fog.tick(g)
    cheats.apply(g, "Steve", "polo")
    cheats.apply(g, "Steve", "polo")
    assert g.reveal == "normal" and lang.english(g.sent[-1]) == 'tellraw Steve "Fog of war: on"'
    g.now = 0.1                                                     # before EVERY seconds: the update comes at once
    fog.tick(g)
    assert lang.english(g.sent[-1]) == f"aoe hide @a[team=p1] {E1}"


def test_polo_keeps_the_units_in_a_siege_tower_hidden():
    g = bare(enemies={E1: "MILITIA", E2: "MILITIA"})
    g.reveal = "normal"
    fog.update(g, {"v": at(10, 10), E1: at(60, 10), E2: at(60, 12)})
    g.towers = {"t": [E1]}
    assert fog.toggle(g) == "all"
    assert g.sent == [f"aoe show @a[team=p1] {E2}"] and g.fog["hidden"] == {E1}


def test_polo_without_hidden_units_sends_no_show_command():
    g = bare()
    g.reveal = "normal"
    cheats.apply(g, "Steve", "polo")
    assert [*map(lang.english, g.sent)] == ['tellraw Steve "Fog of war: off"']
