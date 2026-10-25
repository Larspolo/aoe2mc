"""tools/render.py draws a building design and an area of a world as an isometric PNG."""
import numpy as np
from PIL import Image

import render


def test_render_a_house(tmp_path):
    out = str(tmp_path / "house.png")
    blocks = render.building_blocks("HOUSE", "western")
    W, H = render.render(*blocks, out)
    img = np.asarray(Image.open(out))
    assert img.shape == (H, W, 4) and W > 50 and H > 50
    assert (img[..., 3] == 255).mean() > 0.3                             # the house and its ground cover the image


def test_barriers_are_invisible(tmp_path):
    out = str(tmp_path / "b.png")
    assert render.render([0], [0], [0], ["minecraft:barrier"], out) == (1, 1)
