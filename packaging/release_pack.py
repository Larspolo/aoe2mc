"""The resource pack of a release (#2741): the bytes of the world pack of `aoe2mc.py --resource-pack` (a
deterministic zip, #2738), as aoe2mc-resourcepack.zip. The workflow bundles.yml attaches it to the release of a tag,
and puts its SHA-1 into release.json of each bundle: the game program of the bundle then sends the release link
(game/run.py pack_source).

    python packaging/release_pack.py dist/aoe2mc-resourcepack.zip
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mc  # noqa: E402


def main(out):
    with tempfile.TemporaryDirectory() as d:
        aoe2mc.write_resourcepack(d)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        shutil.copyfile(os.path.join(d, "resourcepacks", "resources.zip"), out)


if __name__ == "__main__":
    main(sys.argv[1])
