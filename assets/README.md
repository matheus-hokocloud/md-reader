# Assets

Pixel art for Markdown Reader. The mascot is a grassland sparrow (see `docs/domain.md`),
always facing left.

| File | What |
|---|---|
| `sparrow.png` | About-dialog illustration, colour, 384×384, transparent. `src/sparrow-1x.png` ×4, nearest-neighbour |
| `icons/mdreader-{16,32,48,64,128,256}.png` | App / window icon: black sparrow, white details, 1 px white outline (reads on light and dark panels) |
| `icons/mdreader.png` | Same as `mdreader-256.png` |
| `github.svg` | GitHub mark (octicons, MIT); not from this pipeline |
| `src/sparrow-1x-raw-pixelized.png` | The 96×96 sprite exactly as the pixel step produced it; source for the fixes |
| `src/sparrow-1x.png` | The 96×96 sprite after hand fixes: eye and eye-ring, yellow lore, pink feet |
| `src/finish_sparrow.py` | Applies those fixes and writes `src/sparrow-1x.png` + `sparrow.png` |
| `src/icon-32.txt`, `src/icon-16.txt` | Hand-drawn icon masters as text grids (`#` black, `w` white, `.` empty) |
| `src/icon-{16,32}-master.png` | Those masters at 1×, outline added |
| `src/build_icon.py` | Masters → `icons/`. 16 and 32 are the masters; 48 = 16×3; 64/128/256 = 32×2/4/8 |

## Where the art came from

**Sparrow illustration:** local ComfyUI (SDXL base 1.0 + `pixel-art-xl` LoRA) in
`/home/virgilio/claude/PixelArt`, specs in `specs/mdreader/`:

1. `sparrow-color.json`, seed **7108**: text-to-image. Gave the pose and the post (facing left).
2. `sparrow-img2img.json`, seed **7302**, denoise 0.5: image-to-image from a crop of 1, adding
   the streaked wing, striped crown and pink legs.
3. `sparrow-px96.json`: `pixelize` of that raw image to a 96×96 sprite, 24 colours.
4. `src/finish_sparrow.py`: hand fixes.

Raw model output: `PixelArt/out/mdreader/sparrow-img2img/20261014-035518/raw_02.png`.

**Icon:** drawn by hand. The model could not produce a clean black/white sparrow at 16 or 32 px
(`specs/mdreader/icon-bw.json` was tried and dropped).

## Regenerate

```bash
python3 assets/src/build_icon.py        # after editing icon-*.txt
python3 assets/src/finish_sparrow.py    # after replacing sparrow-1x-raw-pixelized.png
```

Both need only Pillow. To redo the model step, go to `/home/virgilio/claude/PixelArt` and run
`docker compose run --rm worker gen specs/mdreader/sparrow-img2img.json --seed 7302 -n 1`. The
init image is `out/mdreader/work/a08-crop.png`, a 860 px crop (113,72)–(973,932) of seed 7108's
raw, scaled to 1024. Then run `pixelize <raw> --spec specs/mdreader/sparrow-px96.json` and copy
`px_00.png` to `src/sparrow-1x-raw-pixelized.png`. SDXL results can drift slightly between
GPU/driver versions.
