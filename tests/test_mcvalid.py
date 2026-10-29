"""mcvalid checks with the Minecraft data of the output version."""
import aoe2mc
import mcvalid


def test_default_version_is_the_output_version():
    assert mcvalid.DEFAULT_VERSION == aoe2mc.VERSION_NAME                # the code uses the 26.3 names (#428)
