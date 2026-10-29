"""The button "Save" of the Game menu (#2259, epic #2253): a click saves the running game (the world after
`save-all flush`, with no autosave while it copies, and savegame.json), a green chat line names the save, the menu
closes and the game goes on; `--load` of the folder gives the same state."""
import os

from test_gather import FakeServer, grid

from game import diplomacy, gather, menu, savegame

SLOT = next(k for k, b in diplomacy.BUTTONS.items() if b[1] == "Save")   # the slot of the Save button


def setup(tmp_path):
    world = tmp_path / "World"
    (world / "region").mkdir(parents=True)
    (world / "level.dat").write_bytes(b"level")
    server = FakeServer({})
    server.world = str(world)
    g = gather.Gather(server, grid([[64] * 8 for _ in range(8)], [])).setup()
    g.stock.update(food=123, wood=45)
    g.techs.add("LOOM")
    return server, g


def test_the_game_menu_has_the_save_button(tmp_path):
    server, g = setup(tmp_path)
    diplomacy.open_menu(g, "Steve")
    assert f"{SLOT}:{diplomacy.BUTTONS[SLOT][0]}:Save:" in server.log[-1]


def test_a_click_on_save_writes_the_world_and_the_state_and_the_game_goes_on(tmp_path):
    server, g = setup(tmp_path)
    diplomacy.open_menu(g, "Steve")
    server.scores[menu.OBJECTIVE] = SLOT + 1                           # a click on the slot
    g.clicks()
    saves = os.listdir(tmp_path / "saves")
    assert len(saves) == 1 and saves[0].startswith("World-")
    path = os.path.join(tmp_path, "saves", saves[0])
    assert open(os.path.join(path, "world", "level.dat"), "rb").read() == b"level"
    i = server.log.index("save-off")
    assert server.log[i + 1] == "save-all flush" and "save-on" in server.log[i + 2:]   # autosave on again
    assert "aoe menu-close Steve" in server.log
    assert any(c.startswith("tellraw Steve") and saves[0] in c and "green" in c for c in server.log)
    h = gather.Gather(FakeServer({}), g.data).setup()
    savegame.load(h, savegame.read(path))
    assert h.stock == g.stock and h.techs == g.techs == {"LOOM"}


def test_a_save_takes_the_state_of_all_players_from_the_game(tmp_path):
    server, g = setup(tmp_path)
    other = gather.Gather(server, g.data, player=2)
    server.g = g                                                       # run.play: the Gather of player 1 and its bots
    path = savegame.save(other, "Alex")
    assert set(savegame.read(path)["players"]) == {"1"}
