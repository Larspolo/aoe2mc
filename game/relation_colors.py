"""
The switch "Unique Player Colors" of the Game menu (#5510), as the AoE2 DE option of the same name (Options, Interface):
on (the default, P3) each player has its own color; off, the player sees the colors of the relation (AoE2 DE "Friend
or Foe": COLORS). Vanilla has one color for each scoreboard team (pN) for all clients, so the plugin gives the player
a mirror of the main scoreboard with other team colors (`aoe teamcolors <player> pN=color ...`, RelationColors.java).
The other players see no change. A change of the stances sends the colors again (diplomacy.change).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gather  # noqa: E402

COLORS = {"ally": "yellow",   # the Minecraft team color of each relation (AoE2 DE "Friend or Foe")
          "enemy": "red",
          "neutral": "white",
          "self": "blue"}


def relation(players, me, n):
    """The relation of AoE2 player me to player n: "self", "ally", "neutral" or "enemy"."""
    return "self" if me == n else "ally" if gather.allied(players, me, n) else \
        "neutral" if n in players.get(str(me), {}).get("neutral", ()) else "enemy"


def command(players, person, me):
    """The plugin command that shows the person (AoE2 player me) the relation colors of all players (not Gaia)."""
    return f"aoe teamcolors {person} " + " ".join(
        f"p{n}={COLORS[relation(players, me, n)]}" for n in sorted(int(k) for k in players if int(k) != 0))


def viewers(g):
    """The persons with the relation colors: name -> AoE2 player (kept on the Gather that runs the game)."""
    import diplomacy
    x = diplomacy.main(g)
    if not hasattr(x, "relation_colors"):
        x.relation_colors = {}
    return x.relation_colors


def on(g, person):
    """True when the person sees the relation colors."""
    return person in viewers(g)


def toggle(g, person):
    """The switch: relation colors on or off for the person (the player of g)."""
    v = viewers(g)
    if v.pop(person, None) is not None:
        return g.command(f"aoe teamcolors {person} off")
    v[person] = g.player
    return g.command(command(g.players, person, g.player))


def refresh(g):
    """Send the relation colors again to each person that sees them (after a change of the stances)."""
    for person, me in viewers(g).items():
        g.command(command(g.players, person, me))
