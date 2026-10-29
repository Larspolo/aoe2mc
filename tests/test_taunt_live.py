"""#3318: taunts in the live chat, and the cheats "!mute" and "!nomute"."""
import json

import test_double_bit_axe
from test_cheat_misc import typed

from game import cheats, replay

N = next(iter(replay.TAUNT_SOUNDS))                                    # a taunt of the data with a sound


def taunt(server, g, n):
    """Steve types the taunt n in the chat; returns the commands that follow."""
    server.scores["aoe_taunt"] = n
    server.log.clear()
    g.clicks()
    return list(server.log)


def test_a_taunt_number_shows_its_text_and_plays_its_sound():
    server, g = test_double_bit_axe.setup()
    log = taunt(server, g, int(N))
    text = next(c for c in log if c.startswith("tellraw @a "))
    assert json.loads(text.split(" ", 2)[2])["text"] == "<Steve> " + replay.taunt(N)
    assert f"playsound minecraft:{replay.TAUNT_SOUNDS[N]} master @a[tag=!aoe2mc.mute] ~ ~ ~ 1 1 1" in log
    assert "aoe_taunt" not in server.scores                            # read once
    assert not any(c.startswith(("tellraw", "playsound")) for c in taunt(server, g, 0))


def test_mute_stops_the_taunt_sounds_and_nomute_gives_them_back():
    assert {"!mute", "!nomute"} <= set(cheats.CODES) and "!mute" not in cheats.__doc__.split("Excluded")[1]
    server, g = test_double_bit_axe.setup()
    g.cheats = True
    assert "tag Steve add aoe2mc.mute" in typed(server, g, "!mute")
    assert "tag Steve remove aoe2mc.mute" in typed(server, g, "!nomute")


def test_the_taunt_score_exists_also_with_cheats_off():
    server, g = test_double_bit_axe.setup()
    assert not g.cheats and "scoreboard objectives add aoe_taunt dummy" in server.log
