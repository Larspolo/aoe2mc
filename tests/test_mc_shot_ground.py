"""The stand points of mc_shot.aims are on the ground, so that the sneak pose applies (#3884)."""
import mc_shot


def test_the_stand_feet_of_a_unit_are_at_its_feet_level():
    feet = (10.0, 64.0, 20.0)
    for stand, face in mc_shot.aims((10.0, 65.0, 20.0), dists=(3, 5), feet=feet[1]):
        assert stand[1] == 64.0 and face == (10.0, 65.0 - 1.62, 20.0)
