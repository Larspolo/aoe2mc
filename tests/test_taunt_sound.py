"""A taunt of the live replay plays a vanilla sound when a good Minecraft sound fits it; the other taunts show only
their text (decision #2233, #2662, game/data/taunts.jsonl key "sound")."""
import mcvalid
from test_replay import Fake, data

from game import replay


def chat(text):
    return replay.Replay(Fake(), data([])).commands({"time": 0, "player": 2, "kind": "chat", "text": text})


def test_a_taunt_with_a_sound_plays_it_after_the_text():
    out = chat("1")
    assert out[0].startswith("tellraw @a ") and "Yes." in out[0]
    assert out[1:] == ["playsound minecraft:entity.villager.yes master @a ~ ~ ~ 1 1 1"]
    assert chat("30 lol")[1:] == ["playsound minecraft:entity.evoker.prepare_wololo master @a ~ ~ ~ 1 1 1"]


def test_a_taunt_with_no_sound_and_other_chat_give_only_the_text():
    assert "sound" not in [r for r in replay.table.load("taunts.jsonl") if r["name"] == "14"][0]
    for text in ("14", "hello", "106"):
        assert len(chat(text)) == 1 and chat(text)[0].startswith("tellraw @a ")


def test_each_taunt_sound_is_a_26_3_sound_event():
    assert replay.TAUNT_SOUNDS and all(mcvalid.sound_error(s) is None for s in replay.TAUNT_SOUNDS.values())
    assert mcvalid.sound_error("entity.villager.laugh") == "unknown sound 'entity.villager.laugh'"
