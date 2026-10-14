---
name: project-assets
description: Where Markdown Reader's art lives, how it is generated (PixelArt ComfyUI pipeline), and the established icon/mascot style
metadata:
  type: project
---

Assets live in `assets/` of the md-reader repo (created 2026-10-14 on branch feat/themes-sparrow):
`assets/sparrow.png` (About illustration, colour), `assets/icons/mdreader-*.png` (B/W app icon),
`assets/src/` (1x sprites, hand-drawn icon grids `icon-16.txt`/`icon-32.txt`, `build_icon.py`),
`assets/README.md` (provenance + regen). Specs live outside the repo in
`/home/virgilio/claude/PixelArt/specs/mdreader/`.

Style: pixel art. Mascot = grassland sparrow facing LEFT, perched on a post. Icon = black bird,
white details (eyebrow, eye, wing streaks), NO post (coordinator asked to drop it 2026-10-14), 1 px white 8-connected outline so it reads
on light and dark panels. Icon 48 = 16 master x3; 64/128/256 = 32 master x2/x4/x8.

**Why:** Virgilio asked for a sparrow mascot + B/W icon from his photo (docs/domain.md).
**How to apply:** edit the text grids and rerun build_icon.py rather than editing PNGs;
keep any new art pixel-art and left-facing. See [[pixelart-pipeline-limits]].
