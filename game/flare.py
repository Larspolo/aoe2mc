"""
Flares in the game program (#1234, part of #1230; owner decision #1232: B and C). A flare shows a place to the team:
the players of the team hear a bell, see a column of end_rod particles at the place for SECONDS, and read a chat line.
Two ways to put one: the button "Flare" of the Game menu (diplomacy.BUTTONS) puts it at the ground block that the player
looks at, and the vanilla scoreboard trigger `/trigger aoe_flare` (players without operator rights may use it) puts it
at the place of the player.
The `particle` command with a viewer selector shows the column only to the team (an area_effect_cloud shows it to
all), so tick() sends it again while the flare lives. gather.Gather.clicks calls tick().
"""
import json
import re

OBJECTIVE = "aoe_flare"
SECONDS = 10                                                       # the time of the particle column
SOUND = "minecraft:block.note_block.bell"


def team(player):
    """The viewer selector of the Minecraft players of the team of player name `pN`."""
    return f"@a[team={player}]"


def particles(x, y, z, team):
    """One burst of the column: end_rod particles from the ground up, only for the viewers of team (`force`: also
    far away)."""
    return f"particle minecraft:end_rod {x + 0.5} {y + 4} {z + 0.5} 0.1 4 0.1 0 40 force {team}"


def commands(player, x, y, z, team):
    """The commands of a flare of the Minecraft player `player` at block (x, y, z) for the viewer selector team:
    the bell (minimum volume 1: heard at any distance), the first burst of particles and the chat line."""
    return [f"playsound {SOUND} master {team} {x} {y} {z} 1 1 1",
            particles(x, y, z, team),
            f"tellraw {team} " + json.dumps({"text": f"{player}: Flare at {x} {z}", "color": "gold"})]


def setup(g):
    g.command(f"scoreboard objectives add {OBJECTIVE} trigger")
    g.flares = []


def put(g, player, x, y, z):
    """Put a flare at block (x, y, z) for the team of the Gather g."""
    g.flares = [f for f in getattr(g, "flares", []) if f[3] > g.clock()] + [(x, y, z, g.clock() + SECONDS)]
    return [g.command(c) for c in commands(player, x, y, z, team(f"p{g.player}"))]


def from_look(g, player):
    """The menu button: a flare at the ground block that player looks at. False when the look hits no ground."""
    if not (look := g.look(player)) or not (cell := g.map.pick_ground(*look)):
        return False
    put(g, player, cell[0], g.map.y(*cell), cell[1])
    return True


def tick(g):
    """Enable the trigger, put a flare for each player that used it (at its block), and repeat the particles of the
    live flares."""
    who = getattr(g, "who", "@a")
    g.command(f"scoreboard players enable {who} {OBJECTIVE}")
    sel = who[:-1] + f",scores={{{OBJECTIVE}=1..}}]" if who.endswith("]") else who + f"[scores={{{OBJECTIVE}=1..}}]"
    if "passed" in g.command(f"execute if entity {sel}"):
        for name in g.people():
            if name and re.search(r" has [1-9]", g.command(f"scoreboard players get {name} {OBJECTIVE}")):
                g.command(f"scoreboard players set {name} {OBJECTIVE} 0")
                if pos := g.pos(name):
                    put(g, name, *(int(c // 1) for c in pos))
    if flares := getattr(g, "flares", []):
        g.flares = [f for f in flares if f[3] > g.clock()]
        for x, y, z, _ in g.flares:
            g.command(particles(x, y, z, team(f"p{g.player}")))
