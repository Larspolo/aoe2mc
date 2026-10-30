"""run.py --ai: each bot plays by the rules of its own AoE2 AI script (#4529). The map of test_bot_gather."""
import pytest
from test_bot_gather import bot_map
from test_bot_levels import FakeGather, Stop

from game import bot, per, run
from game.bot import build, train                                     # the modules that per uses

SCRIPT = """(defrule (civilian-population < 10) (can-train villager) => (train villager))
(defrule (housing-headroom < 2) (can-build house) => (build house))"""


def scripted(text):
    server, me, b = bot_map()
    b.script = per.Script(per.parse(text), b)
    return b


def queued(b):
    return {e["name"] for q in b.g.queues.values() for e in q}


def test_the_bot_trains_and_builds_only_by_its_script():
    b = scripted(SCRIPT)
    b.g.techs.update(build.AGE_TECHS[:1])                              # the buildings of ORDER are free to build
    b.g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    b.g.pop = train.limit(b.g) - 1                                     # a headroom of 1: a house
    b.step()
    assert queued(b) == {"VILLAGER_MALE"} and [s["name"] for s in b.g.sites] == ["HOUSE"]
    b.g.aegis = True
    for _ in range(200):
        b.step()
    assert {s["name"] for s in b.g.sites} == {"HOUSE"}                 # no building of ORDER without a rule
    assert queued(b) <= {"VILLAGER_MALE"}


def test_a_bot_without_a_script_builds_its_order():
    server, me, b = bot_map()
    b.g.techs.update(build.AGE_TECHS[:1])
    b.g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    b.g.pop = 1
    b.step()
    assert b.script is None and [s["name"] for s in b.g.sites] == [n for n in bot.ORDER if not build.locked(b.g, n)][:1]


def test_a_missing_file_names_its_path(capsys, tmp_path):
    with pytest.raises(SystemExit):
        run.main(["WORLD", "--play", "--bot", "--ai", str(tmp_path / "none.per")])
    assert f"no AI script {tmp_path / 'none.per'}" in capsys.readouterr().err


def test_each_bot_gets_its_own_script_in_seat_order(monkeypatch, tmp_path):
    import bot as bots
    import combat
    import gather as gathers
    from test_play_speed import FakeGame
    seen = []

    class Stub:
        g = type("G", (), {"villagers": []})()

        def setup(self):
            return self

    def bot_of(game, data, **kw):
        seen.append(kw.get("script"))
        if len(seen) == 3:
            raise Stop
        return Stub()

    (tmp_path / "a.per").write_text("(defrule (true) => (train villager))")
    (tmp_path / "b.per").write_text("(defrule (true) => (build house))")
    monkeypatch.setattr(bots, "Bot", bot_of)
    monkeypatch.setattr(gathers, "Gather", FakeGather)
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    monkeypatch.setattr(run, "bot_seats", lambda players, people, n: [(2, 1), (3, 1), (4, 1)])
    (tmp_path / "aoe2mc.json").write_text('{"players": {"1": {}, "2": {}, "3": {}, "4": {}}, "tile_size": 4}')
    files = run.script_list(f"{tmp_path / 'a.per'},{tmp_path / 'b.per'}")
    with pytest.raises(Stop):
        run.play(FakeGame(), str(tmp_path), bot=3, ai=files)
    assert [r[0].actions[0][0] for r in seen[:2]] == ["train", "build"] and seen[2] is None
