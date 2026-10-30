"""tools/render.py draws a building design and an area of a world as an isometric PNG."""
import numpy as np
import render
from PIL import Image


def test_render_a_house(tmp_path):
    out = str(tmp_path / "house.png")
    blocks = render.building_blocks("HOUSE", "western")
    W, H = render.render(*blocks, out)
    img = np.asarray(Image.open(out))
    assert img.shape == (H, W, 4) and W > 50 and H > 50
    assert (img[..., 3] == 255).mean() > 0.3                             # the house and its ground cover the image


def test_cut_view_shows_the_inside(tmp_path):
    xs, ys, zs, states = render.building_blocks("HOUSE", "western")
    cx, cy, cz, cut = render.building_blocks("HOUSE", "western", cut=2)
    ground = min(y for y, s in zip(ys, states) if "grass_block" in s)
    assert cy.max() == ground + 2 and ys.max() > ground + 2 and len(cut) < len(states)
    W, H = render.render(cx, cy, cz, cut, str(tmp_path / "cut.png"))
    assert W > 50 and H > 50


def test_barriers_are_invisible(tmp_path):
    out = str(tmp_path / "b.png")
    assert render.render([0], [0], [0], ["minecraft:barrier"], out) == (1, 1)


def test_texture_colors():
    rgb, clear = render.colors(["minecraft:mud_bricks", "minecraft:grass_block[snowy=false]", "minecraft:glass"])
    r, g, b = rgb[0, 0]
    assert r > b and abs(r - g) < 50 and r < 180                   # mud bricks are brown, not red brick
    assert rgb[1, 0, 1] > rgb[1, 0, 0] and rgb[1, 1, 0] > rgb[1, 1, 1]   # grass: green top, brown side
    assert list(clear) == [False, False, True]


def test_sheet_has_a_row_for_each_architecture_set(tmp_path):
    import buildings
    W, H = render.sheet("HOUSE", str(tmp_path / "s.png"), variants=1, scale=2)
    assert H > len(buildings.ARCH) * 16
