---
name: pixelart-pipeline-limits
description: Behaviour and limits of the shared local ComfyUI (SDXL + pixel-art-xl) pipeline at /home/virgilio/claude/PixelArt
metadata:
  type: reference
---

`/home/virgilio/claude/PixelArt`: `docker compose run --rm worker gen specs/<x>.json`; specs dir is
mounted read-only in the worker (write specs from the host). ComfyUI (`pixelart-comfyui`) is
SHARED — other agents queue Wan 2.2 video jobs, so an image can take 2–4 min instead of ~10 s.
Never stop/restart it.

Observed 2026-10-14: SDXL+LoRA gives good colour birds but ignores facing direction (~1/4 face
left), puts "yellow spot" on the breast, and can't do clean 1-bit icons — the auto pixel step
floods white bodies into a white background. `fit` pads with black, so don't use it with a
white background; crop on the host and `pixelize` instead. Small icons: hand-pixel.
