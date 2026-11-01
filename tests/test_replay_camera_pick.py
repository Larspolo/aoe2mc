"""#5440: with --camera player the view center is 8-20 blocks from the units. The info line picks the unit nearest
to the ray up to CAMERA_PICK blocks; without the camera the radius stays 0.8."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402

EYE, SOUTH = (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)                     # the feet + 1 of a unit are on y = 1


def test_a_camera_ray_15_blocks_from_the_unit_picks_it():
    assert gather.pick_unit(EYE, SOUTH, {7: (15.0, 0.0, 30.0)}, radius=replay.CAMERA_PICK) == 7


def test_the_nearest_unit_to_the_camera_ray_wins():
    units = {7: (15.0, 0.0, 30.0), 8: (2.0, 0.0, 40.0)}
    assert gather.pick_unit(EYE, SOUTH, units, radius=replay.CAMERA_PICK, ray=True) == 8


def test_without_the_camera_a_ray_0_9_blocks_from_a_unit_picks_none():
    assert gather.pick_unit(EYE, SOUTH, {7: (0.9, 0.0, 10.0)}) is None
