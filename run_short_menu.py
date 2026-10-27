"""game/run.py for this owner session only: a menu command longer than the RCON limit (1446 bytes) loses its lore
lines (cost, time, help text), so that the server does not close RCON (bug ticket of the /human session)."""
import sys
sys.path[:0] = ["/Users/polo/aoe2mc/game", "/Users/polo/aoe2mc/tools", "/Users/polo/aoe2mc"]
import menu  # noqa: E402

LIMIT = 1446
orig = menu.command


def command(player, title, items):
    cmd = orig(player, title, items)
    if len(cmd.encode()) <= LIMIT:
        return cmd
    items = [(slot, mat, name, "", *more) for slot, mat, name, _lore, *more in items]
    cmd = orig(player, title, items)
    print(f"short menu {title}: {len(cmd.encode())} bytes", file=sys.stderr, flush=True)
    return cmd


menu.command = command
import run  # noqa: E402
sys.argv[0] = "/Users/polo/aoe2mc/game/run.py"
run.main()
