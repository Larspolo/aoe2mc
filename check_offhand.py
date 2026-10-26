"""Check of #966: a player who joins a converted world gets the map of the world in the off-hand."""
import sys, time
R = "/home/user/aoe2mc"
sys.path[:0] = [R, R + "/game", R + "/tools"]
import mc_shot  # noqa
from game import run  # noqa

S = sys.argv[1]
with run.Game(S + "/vilW2") as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    time.sleep(4)                                        # the pulse runs every 2 s
    print("hand:", game.command("data get entity aoe2mc equipment.offhand")[:200], flush=True)
    print("tags:", game.command("data get entity aoe2mc Tags")[:120], flush=True)
    game.command("gamemode adventure aoe2mc")
    game.command("tp aoe2mc 72.5 68 82.5 -135 10")
    time.sleep(20)
    client.shot(f"{S}/check/offhand_server.png")
    time.sleep(3)                                        # a second pulse must not give a second map
    print("hand2:", game.command("data get entity aoe2mc equipment.offhand")[:200], flush=True)
    print("inv:", game.command("data get entity aoe2mc Inventory")[:200], flush=True)
