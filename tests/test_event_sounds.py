"""The AoE2 event sounds (#3502, train.EVENT_SOUNDS): a complete own site, a complete own technology and a monk
conversion each play one vanilla sound. Fake server, no Minecraft."""
import mcvalid
from test_build_done import done
from test_convert_owner import MAP, objects
from test_gather import FakeServer, grid
from test_loom import setup

from game import gather, monk, train


def test_a_complete_site_plays_the_built_sound_for_its_owner_team():
    server, g, cells = done("LUMBER_CAMP")
    sounds = [c for c in server.log if "block.anvil.use" in c]
    assert len(sounds) == 1 and sounds[0].startswith("playsound minecraft:block.anvil.use master @a[team=p1] ")
    assert sounds[0].endswith(" ~ 8.0 1 1")                              # the middle of the site


def test_a_complete_technology_plays_the_bell_and_an_age_does_not():
    server, g = setup(food=1000, gold=1000)
    train.research(g, {"name": "LOOM", "player": 1})
    assert server.log.count("playsound minecraft:block.note_block.bell master @a[team=p1] ~ ~ ~ 1 1") == 1
    train.research(g, {"name": "LOOM", "player": 1}, start=True)
    assert sum("block.note_block.bell" in c for c in server.log) == 1


def test_a_monk_conversion_plays_the_wololo_sound_at_the_unit():
    server = FakeServer({"monk": {"Pos": (3.5, 64.0, 2.5)}, "foe": {"Pos": (13.5, 64.0, 12.5)}})
    g = gather.Gather(server, grid(MAP, objects())).setup()
    monk.take(g, "foe")
    assert server.log.count("execute at foe run playsound minecraft:entity.evoker.prepare_wololo master @a ~ ~ ~ 1 1") == 1


def test_each_event_sound_is_a_26_3_sound_event():
    assert set(train.EVENT_SOUNDS) == {"built", "convert", "research"}
    assert all(mcvalid.sound_error(s) is None for s in train.EVENT_SOUNDS.values())
