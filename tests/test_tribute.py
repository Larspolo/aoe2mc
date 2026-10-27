"""game/diplomacy.py: the Game menu hotbar item opens a chest menu with a "Diplomacy" page, and a click there sends a
tribute of 100 to another player: the sender pays 130 (the AoE2 fee of 30 % on top, AoE2 wiki "Tribute"), the receiver
gets 100. A player needs a complete own market (#1588). Fake server."""
import types
from urllib.parse import unquote

from test_gather import FakeServer, grid

from game import diplomacy, gather, menu


class Server(FakeServer):
    """Steve holds the Game menu item and right clicks it."""

    def command(self, cmd):
        if "weapon.mainhand *[custom_data={aoe_game_menu:1b}]" in cmd:
            self.log.append(cmd)
            return "Test passed"
        return super().command(cmd)


def setup(market=True):
    objects = [{"kind": "building", "name": "MARKET", "player": 1, "footprint": [2, 2, 6, 6]}] * market
    players = {"0": {}, "1": {"color": "blue"}, "2": {"color": "red", "civ": "FRANKS"}, "3": {"color": "green"}}
    server = Server({})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects) | {"players": players}).setup()
    g.stock.update(food=500, wood=200, gold=0, stone=130)
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_each_player_gets_the_game_menu_item_in_a_free_hotbar_slot():
    server, g = setup()
    g.clicks()
    give = [c for c in server.log if "aoe_game_menu" in c and "item replace" in c]
    assert give and give[0].endswith(f"hotbar.{diplomacy.SLOT} with {diplomacy.ITEM}")
    assert diplomacy.SLOT not in {slot for slot, _ in gather.GROUPS.values()}


def test_a_click_on_the_item_opens_the_game_menu_and_its_diplomacy_page():
    server, g = setup()
    server.scores["aoe_use"] = 1
    assert g.clicks() == []                                            # no ray: no order to the units
    assert menus(server)[-1].startswith("aoe menu Steve Game menu 0:writable_book:Diplomacy:")
    server.scores[menu.OBJECTIVE] = 1                                  # a click on "Diplomacy"
    g.clicks()
    page = menus(server)[-1]
    assert page.startswith("aoe menu Steve Diplomacy ")
    assert "0:red_wool:Player 2 (Franks):" in page and "1:green_wool:Player 3:" in page
    assert "9:wheat:Send 100 food:130 food with the fee" in page and "37:cobblestone:Send 100 stone:" in page
    assert "Player 1" not in page                                      # not the own column


def test_a_tribute_moves_100_to_the_receiver_and_the_sender_pays_the_fee():
    server, g = setup()
    bot = types.SimpleNamespace(g=gather.Gather(server, g.data, player=2))
    g.bots = [bot]
    food = bot.g.stock["food"]
    assert diplomacy.order(g, "Steve", 9) == 1                         # food to player 2
    assert g.stock["food"] == 370 and bot.g.stock["food"] == food + 100
    assert "scoreboard players remove Food aoe_res 130" in server.log
    assert f"scoreboard players add Food {bot.g.board} 100" in server.log
    assert diplomacy.order(g, "Steve", 9, shift=True) == 2             # a shift click: while the stock allows
    assert g.stock["food"] == 110 and bot.g.stock["food"] == food + 300
    assert diplomacy.order(g, "Steve", 19) == 1                        # wood to player 3: no program plays it
    assert g.stock["wood"] == 70 and g.tributes == {3: {"food": 0, "wood": 100, "gold": 0, "stone": 0}}


def test_a_sender_with_less_than_the_amount_and_the_fee_sends_nothing():
    server, g = setup()
    assert diplomacy.order(g, "Steve", 27) == 0                        # 0 gold
    assert diplomacy.order(g, "Steve", 18, shift=True) == 1 and g.stock["wood"] == 70   # 200 wood: 130 for one
    assert g.stock["gold"] == 0 and any("Not enough gold." in c for c in server.log)
    assert diplomacy.order(g, "Steve", 36) == 1 and g.stock["stone"] == 0   # exactly 130 stone


def test_a_player_without_a_market_sends_nothing():
    server, g = setup(market=False)
    assert diplomacy.order(g, "Steve", 9) == 0 and g.stock["food"] == 500
    assert any("Build a market to send tribute." in c for c in server.log)
