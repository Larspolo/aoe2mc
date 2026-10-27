"""mark.py SHOT LOG TAG OUT: crop the map of a screenshot, scale it up and circle the map pixels of the logged units."""
import re
import sys

from PIL import Image, ImageDraw

shot, log, tag, out = sys.argv[1:5]
im = Image.open(shot).convert("RGB")
x0, y0, x1, y1 = (int(v) for v in sys.argv[5:9])          # the map interior on the screen
print("map on screen", round(x0), round(y0), round(x1), round(y1))
k = (x1 - x0) / 128
crop = im.crop((round(x0), round(y0), round(x1), round(y1))).resize((768, 768), Image.NEAREST)
d, f = ImageDraw.Draw(crop), 768 / 128
for ln in open(log):
    m = re.match(rf"{tag} unit (\S+) team (\S+) pos .* Minimap pixel: (\d+) (\d+)", ln)
    if m and m[2] != "None":
        px, pz = int(m[3]) + 1, int(m[4]) + 1                       # the center of the 2 x 2 dot
        d.ellipse((px * f - 14, pz * f - 14, px * f + 14, pz * f + 14), outline="white", width=2)
        d.text((px * f + 16, pz * f - 8), f"{m[1]} p{m[2]}", fill="white")
crop.save(out)
