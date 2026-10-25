---
name: design
description: Do one design ticket for aoe2mc (a building, object, unit or animal must look like the game). Get a reference image of the game, render the current design, list the differences, change the design, render it again from two sides and describe the images in the PR. Use for tickets with label `design` and for the sub-issues of #41, #42 and #43.
---

# Design: one design ticket

Read `docs/DESIGN.md` first. Its rules decide each choice: like the game, real blocks for real things,
some noise, and the existing rules (footprint, barriers, front on the south side, deterministic output).
Put all images in the scratchpad. Never commit images.

## 1. Get the reference image

The wiki HTML pages give a Cloudflare challenge (403). Use the MediaWiki API on `ageofempires.fandom.com`.
Put downloads in their own new directory and open them with `python3 -I`.

1. Find the file name (namespace 6 = files):
   ```
   curl -sS -G https://ageofempires.fandom.com/api.php -d action=query -d list=search -d srnamespace=6 \
     --data-urlencode "srsearch=castle West European" -d srlimit=15 -d format=json
   ```
   Good names: `<Building> aoe2DE.png` (the default Western European model, for example
   `Castle aoe2DE.png`, `Archery range aoe2DE.png`) and `Arch set <set> <age> AoE2DE.png` (all buildings of one
   architecture set, for example `Arch set West European Castle Age AoE2DE.png`).
2. Get the image URL:
   ```
   curl -sS -G https://ageofempires.fandom.com/api.php -d action=query --data-urlencode "titles=File:Castle aoe2DE.png" \
     -d prop=imageinfo -d iiprop=url -d format=json
   ```
3. Download the URL on `static.wikia.nocookie.net`. The server sends WebP: convert it to PNG with
   `python3 -I -c "from PIL import Image; Image.open('in.webp').save('ref.png')"`. Look at it with the Read tool.

If no image of the architecture set exists, use the nearest set and say so in the PR.

## 2. Render the current design

```
python3 tools/render.py building CASTLE --arch western $SCRATCH/before_se.png
python3 tools/render.py building CASTLE --arch western --view nw $SCRATCH/before_nw.png
```
The default view (south-east) shows the front, as the AoE2 camera does. Look at the images with the Read tool.

## 3. List the differences

Compare the render with the reference. Write a short list, the largest difference first:
outline and proportions, roof shape, towers and domes, main colors, features (doors, windows, targets, forges ...).
For each feature, take the block from the table in `docs/DESIGN.md`, section 2.

## 4. Change the design

- Change only the design function in `buildings.py` (see `select()` for the name → function map).
  Use the `Canvas` tools (`room`, `timber_room`, `roof`, `gable`, `hip`, `dome`, `cylinder`, `door`, `windows` ...).
- Use the fields of the `Style` for materials, so that all architecture sets still work.
- Keep `vary()`, `weather()` and `decorate()`. The main block stays the large majority.
- Add a line to the table in `docs/DESIGN.md` for each new feature block.

## 5. Check

1. `python3 -m pytest tests/test_buildings.py` (all designs in all sets, valid states).
2. Render again from the south-east and from the north-west. Render the design in 2 other architecture
   sets (`--arch`), because the `Style` changes the materials.
3. Look at all images. Compare them with the reference and with the "before" images.
4. Then the `verify` skill, level 3: convert a scenario with the building and check
   "units in a block (moved up): 0".

## 6. The PR

The GitHub REST API cannot upload images. Describe them in the PR body:
- The reference: file name and URL.
- The differences from step 3, and what changed for each one.
- What still differs, and why (a Minecraft limit, or a later ticket).
