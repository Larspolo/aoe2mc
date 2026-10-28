"""A saved game keeps its game settings and the state of the bot (#2325, epic #2253): `--load SAVE` alone starts the
game with the settings of the save, an option given with `--load` wins, and the bot goes on with its attack time and
its wave."""
import os

from test_bot_gather import bot_map

from game import run, savegame


def main(tmp_path, monkeypatch, argv, at=400.0, save=True):
    """run.main with a fake server: the fake play gives the game a player and a bot that attacked at `at` game seconds,
    and the end of main saves it (save: a second save in the same second has the same name). Returns the options of play and the save folders."""
    world = tmp_path / "World"
    world.mkdir(exist_ok=True)
    (world / "level.dat").write_bytes(b"level")
    calls = {}

    class Game:
        def __init__(self, world, version, server):
            self.world, self.port, self.game_port = world, 0, 0

        def start(self):
            pass

        def stop(self):
            pass

    def play(game, world, log, cheats, bot, **kw):
        server, me, b = bot_map()
        b.time, b.charged, b.attack = at, True, 300.0
        me.bots = [b]
        server.settings = game.settings                                # the Gather of a real game has .game = Game
        game.g = me if save else None
        calls.update(cheats=cheats, bot=bot, **kw)
    monkeypatch.setattr(run, "Game", Game)
    monkeypatch.setattr(run, "play", play)
    monkeypatch.setattr(run, "console", lambda game: None)
    run.main([str(world), "--play", *argv])
    return calls, sorted(os.listdir(tmp_path / "saves"))


def test_load_alone_takes_the_settings_and_the_bot_of_the_save(tmp_path, monkeypatch):
    first, saves = main(tmp_path, monkeypatch, ["--reveal", "all", "--cheats", "--all-techs", "--bot",
                                                "--bot-attack", "5:00", "--victory", "conquest"])
    path = str(tmp_path / "saves" / saves[0])
    calls, _ = main(tmp_path, monkeypatch, ["--load", path], save=False)
    state = calls.pop("state")
    assert calls == {k: v for k, v in first.items() if k != "state"}
    assert calls["reveal"] == "all" and calls["cheats"] and calls["all_techs"] and calls["bot"]
    assert calls["bot_attack"] == "5:00" and calls["victory"] == "conquest"
    server, me, b = bot_map()
    me.bots = [b]
    savegame.load(me, state)
    assert (b.time, b.charged, b.attack) == (400.0, True, 300.0)


def test_an_option_given_with_load_wins_over_the_save(tmp_path, monkeypatch):
    _, saves = main(tmp_path, monkeypatch, ["--reveal", "all", "--cheats", "--bot", "--bot-attack", "5:00"])
    path = str(tmp_path / "saves" / saves[0])
    calls, _ = main(tmp_path, monkeypatch, ["--load", path, "--reveal", "normal", "--bot-attack", "12:00"], save=False)
    assert calls["reveal"] == "normal" and calls["bot_attack"] == "12:00" and calls["cheats"]
    server, me, b = bot_map()
    me.bots = [b]
    savegame.load(me, calls["state"])
    assert b.attack == bot_map()[2].attack and b.time == 400.0          # the given attack time wins too


def test_a_save_without_settings_loads_with_the_options_of_the_command_line(tmp_path, monkeypatch):
    _, saves = main(tmp_path, monkeypatch, ["--reveal", "all", "--cheats"])
    path = str(tmp_path / "saves" / saves[0])
    state = savegame.read(path)
    del state["settings"]
    for p in state["players"].values():
        p.pop("bot", None)
    with open(os.path.join(path, savegame.FILE), "w") as f:
        savegame.json.dump(state, f)
    calls, _ = main(tmp_path, monkeypatch, ["--load", path, "--people", "2"], save=False)
    assert calls["reveal"] == "normal" and not calls["cheats"] and calls["people"] == 2
    server, me, b = bot_map()
    me.bots = [b]
    savegame.load(me, calls["state"])
    assert (b.time, b.charged) == (0.0, False)
