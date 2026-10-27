"""game/watch.py with the follow camera of player 1, and the owner in adventure mode (the fix of #1642)."""
import sys
sys.path[:0] = ["/Users/polo/aoe2mc/game"]
import run  # noqa: E402
import watch  # noqa: E402

orig = run.replay
run.replay = lambda game, world, speed=1.0, start="0:00", follow=None, guide=None, view=None: \
    orig(game, world, speed, start, 1, guide, view)
cmd = run.Game.command
run.Game.command = lambda self, c: cmd(self, "gamemode adventure @a" if c == "gamemode creative @a" else c)
watch.main(sys.argv[1:])
