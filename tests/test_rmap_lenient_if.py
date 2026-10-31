"""Forms of AoE2 random map scripts that AoE2 DE accepts (#4931): a stray endif or end_random, an if with no endif at
the end, and an avoid_actor_area with no number (Gold_Rush, Karsts, Continental, Mountain_Dunes)."""
import numpy as np
from test_rmap import SCRIPT, make

import rmap


def expand(text, defined=()):
    return rmap.expand(rmap.tokens(text), np.random.default_rng(0), set(defined), {}, [])


def test_a_stray_endif_after_a_block_is_skipped():
    assert expand("create_object GOLD { if A x 1 endif set_scale_by_groups } endif y") == \
        ["create_object", "GOLD", "{", "set_scale_by_groups", "}", "y"]


def test_a_stray_end_random_is_skipped():
    assert expand("a end_random b") == ["a", "b"]


def test_an_if_that_ends_inside_a_block_and_extra_endifs_after_it():
    assert expand("if A c { if B d else e endif endif } endif endif f", {"A"}) == ["c", "{", "e", "}", "f"]


def test_an_if_with_no_endif_at_the_end_is_accepted():
    assert expand("a if A b", {"A"}) == ["a", "b"]
    assert expand("a if A b") == ["a"]


def test_a_script_with_a_stray_endif_gives_the_same_land():
    assert make(3, script=SCRIPT + "\nendif\n")[0] == make(3)[0]


def test_an_avoid_actor_area_with_no_number_avoids_nothing():
    base = "<OBJECTS_GENERATION>\ncreate_object STONE { number_of_objects 6 %s }\n"
    a, _ = make(3, script=SCRIPT + base % "avoid_actor_area")
    b, _ = make(3, script=SCRIPT + base % "")
    assert a == b
