"""Orders to units with their Minecraft AI, on the Paper server of the game program (#436).

The plugin (game/plugin) does the work: `aoe moveto` walks a unit on a Minecraft path, `aoe attack` sets its
target. An order turns on the AI of a unit and keeps only the goals that fit AoE2 (attack and swim): a unit stands
still without an order and attacks only the target of an order, not a unit of its own team.

This module gives each unit the walk speed of its AoE2 unit (the attribute movement_speed) just before the order:
the entity is loaded then (an RCON command reaches only the entities of loaded chunks, #358).

    import ai
    game.command(ai.speed_command(uuid, "MILITIA", T))
    ai.move(game, uuid, "MILITIA", T, x, y, z)
    ai.attack(game, [uuid, ...], names, T, target_uuid)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gather import NORMAL  # noqa: E402
from replay import SPEEDS  # noqa: E402
from units import siege  # noqa: E402

# Walk speed on a Minecraft path, blocks per second = WALK * movement_speed ** 2 (the mob input is the speed, and
# the step is the input times the speed). Measured on Paper 26.3 on flat stone, attribute 0.15 to 0.6: zombie 43.1
# to 44.1, cow 43.0, horse 39.8 (#436), villager 42.3 to 44.3 (#437: NoAI villagers on stone bricks, as the zombies).
WALK = 43.4


def walk_speed(name, T, rate=NORMAL):
    """Blocks per real second of AoE2 unit `name` at `rate` game seconds per real second (default: Normal game
    speed): tiles per game second * T * rate."""
    return next((s for k, s in SPEEDS.items() if name.startswith(k)), 1.0) * T * rate


def movement_speed(name, T, rate=NORMAL):
    return round(math.sqrt(walk_speed(name, T, rate) / WALK), 4)


def speed_command(uuid, name, T, rate=NORMAL):
    if siege(name):                                    # a minecart: the attribute is on its carrier (plugin, #836)
        return f"aoe speed {uuid} {movement_speed(name, T, rate)}"
    return f"attribute {uuid} minecraft:movement_speed base set {movement_speed(name, T, rate)}"


def move(game, uuid, name, T, x, y, z, rate=NORMAL):
    """Walk unit `uuid` (AoE2 unit `name`) to block position (x, y, z). Returns the answer of the plugin. A trebuchet
    of the game program packs first (trebuchet.move, #1351)."""
    if name == "TREBUCHET" and hasattr(game, "soldiers"):
        import trebuchet                                            # gather imports trebuchet and this module: late
        return trebuchet.move(game, uuid, [speed_command(uuid, name, T, rate), f"aoe moveto {uuid} {x} {y} {z}"])
    game.command(speed_command(uuid, name, T, rate))
    return game.command(f"aoe moveto {uuid} {x} {y} {z}")


def attack(game, uuids, names, T, target, rates=None):
    """Send units `uuids` (AoE2 units `names`) to attack entity `target`, at the `rates` of each unit (default
    Normal game speed; train.speed with the trigger changes of the unit, #3083). Units of the team of the target stay."""
    for uuid, name, rate in zip(uuids, names, rates or [NORMAL] * len(uuids)):
        game.command(speed_command(uuid, name, T, rate))
    return [game.command(f"aoe attack {uuid} {target}") for uuid in uuids]
