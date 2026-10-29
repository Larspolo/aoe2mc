"""game/civs.py: Persian town centers and docks have double hit points (AoE2 DE wiki, "Persians", #1895), also the
town center of the map; Masonry multiplies after the bonus."""
from test_forging import setup

from game import build, combat


def game(civ):
    _, g = setup(age=0)
    g.data["players"] = {"1": {"civ": civ}}
    return g


def tc_hp(civ, techs=()):
    return build.values(game(civ), "TOWN_CENTER", set(techs)).hp


def test_persian_town_centers_and_docks_have_more_hit_points():
    g = game("PERSIANS")
    assert tc_hp("PERSIANS") > tc_hp("BRITONS") == combat.stats("TOWN_CENTER").hp
    assert build.values(g, "DOCK").hp > combat.stats("DOCK").hp
    assert build.values(g, "BARRACKS").hp == combat.stats("BARRACKS").hp


def test_masonry_multiplies_after_the_bonus():
    assert tc_hp("PERSIANS", {"MASONRY"}) == round(tc_hp("PERSIANS") * tc_hp("BRITONS", {"MASONRY"}) / tc_hp("BRITONS"))


class Game:
    def __init__(self):
        self.sent = []

    def command(self, cmd):
        self.sent.append(cmd)
        return "Stats: 1 units"


def test_the_town_center_of_the_map_of_a_persian_player_has_double_hit_points():
    tc = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [0, 0, 16, 16]}
    data = {"objects": [tc, dict(tc, player=2, footprint=[32, 0, 48, 16])],
            "players": {"1": {"civ": "PERSIANS"}, "2": {"civ": "BRITONS"}}}
    game = Game()
    combat.setup(game, data)
    hp = {c.split()[2]: int(c.split()[3]) for c in game.sent if c.startswith("aoe building ")}
    assert hp == {combat.target_uuid([0, 0, 16, 16]): tc_hp("PERSIANS"), combat.target_uuid([32, 0, 48, 16]): tc_hp("BRITONS")}


def test_the_attack_mark_shows_the_full_hit_points_of_a_persian_town_center():
    g = game("BRITONS")
    g.data["players"]["2"] = {"civ": "PERSIANS"}
    g.fort_names["t"], g.fort_players["t"], g.forts["t"] = "TOWN_CENTER", 2, (20, 64, 20, 23, 70, 23)
    g.look, g.target = lambda name: ((0, 70, 0), (1, 0, 0)), lambda *a: ("fort", "t", None)   # the ray hits it
    g.game.log.clear()
    g.click("Steve")
    assert any(f'"/{tc_hp("PERSIANS")})"' in c for c in g.game.log if "actionbar" in c)
