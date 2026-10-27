"""Draw the app icon of the installers (#1542): a grass block with a stone tower in the player blue. An own image, not
an AoE2 or Minecraft logo (docs/THIRD_PARTY.md). Writes icon.png, icon.ico (Windows) and icon.icns (macOS) into the
folder of the argument (default: packaging/). Run: python packaging/icon.py [FOLDER]."""
import os
import sys

from PIL import Image, ImageDraw

GRASS, DIRT, STONE, DARK, BLUE = (106, 170, 64), (134, 96, 67), (150, 150, 150), (96, 96, 96), (52, 84, 196)


def draw(n=512):
    """The icon at n × n pixels on a 16 × 16 grid: a block (grass top, dirt sides) with a tower and a banner."""
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d, u = ImageDraw.Draw(img), n // 16

    def box(x0, y0, x1, y1, color):
        d.rectangle([x0 * u, y0 * u, x1 * u - 1, y1 * u - 1], fill=color)
    box(1, 9, 15, 15, DIRT)                                            # the block
    box(1, 9, 15, 11, GRASS)
    for x in range(1, 15, 3):                                          # grass that hangs over the dirt
        box(x, 11, x + 1, 12, GRASS)
    box(5, 3, 11, 10, STONE)                                           # the tower
    for x in (5, 7, 9):                                                # the merlons
        box(x, 1, x + 1 + (x == 9), 3, STONE)
    box(7, 6, 9, 10, DARK)                                             # the door
    box(10, 4, 11, 7, BLUE)                                            # the banner in the player color
    return img


def main(folder=os.path.dirname(os.path.abspath(__file__))):
    img = draw()
    img.save(os.path.join(folder, "icon.png"))
    img.save(os.path.join(folder, "icon.ico"), sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    img.save(os.path.join(folder, "icon.icns"))


if __name__ == "__main__":
    main(*sys.argv[1:])
