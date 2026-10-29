"""A taunt of the live replay plays a vanilla sound when a good Minecraft sound fits it; the other taunts show only
their text (decision #2233, #2662, game/data/taunts.jsonl key "sound")."""
import mcvalid
from test_replay import Fake, data

from game import replay

SOUND = sorted(replay.TAUNT_SOUNDS, key=int)                           # the taunts of the data with a sound
TEXT = [n for n in sorted(replay.TAUNTS, key=int) if n not in replay.TAUNT_SOUNDS]   # and with only a text


def chat(text):
    return replay.Replay(Fake(), data([])).commands({"time": 0, "player": 2, "kind": "chat", "text": text})


def test_a_taunt_with_a_sound_plays_it_after_the_text():
    n = SOUND[0]
    out = chat(n)
    assert out[0].startswith("tellraw @a ") and replay.TAUNTS[n].strip("()") in out[0]
    assert out[1:] == [f"playsound minecraft:{replay.TAUNT_SOUNDS[n]} master @a ~ ~ ~ 1 1 1"]
    assert chat(f"{SOUND[-1]} lol")[1:] == [f"playsound minecraft:{replay.TAUNT_SOUNDS[SOUND[-1]]} master @a ~ ~ ~ 1 1 1"]


def test_a_taunt_with_no_sound_and_other_chat_give_only_the_text():
    for text in (TEXT[0], "hello", str(max(map(int, replay.TAUNTS)) + 1)):
        assert len(chat(text)) == 1 and chat(text)[0].startswith("tellraw @a ")


def test_each_taunt_sound_is_a_26_3_sound_event():
    assert replay.TAUNT_SOUNDS and all(mcvalid.sound_error(s) is None for s in replay.TAUNT_SOUNDS.values())
    assert mcvalid.sound_error("entity.villager.laugh") == "unknown sound 'entity.villager.laugh'"
