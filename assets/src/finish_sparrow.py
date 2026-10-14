"""Hand fixes on the pixelized sparrow, then the x4 About illustration.

  python3 assets/src/finish_sparrow.py

In:  assets/src/sparrow-1x-raw-pixelized.png  (pixelgen output, 96x96, untouched)
Out: assets/src/sparrow-1x.png                (96x96, fixed)
     assets/sparrow.png                       (384x384, nearest-neighbour x4)

Fixes: the model's 5x5 black eye blob -> 2x2 pupil with a pale eye-ring and a brown
stripe behind it; a yellow lore spot between beak and eye; reddish/white feet -> pink.
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.dirname(HERE)

PUPIL, RING, FACE, PALE, BROWN = '#251a1d', '#d5cbd1', '#948183', '#bbaaa9', '#643c28'
YELLOW, YELLOW_DK = '#f2c94c', '#c9a227'
PINK, PINK_DK = '#d39a8e', '#9a5c55'


def rgba(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def main():
    im = Image.open(os.path.join(HERE, 'sparrow-1x-raw-pixelized.png')).convert('RGBA')
    put = lambda x, y, c: im.putpixel((x, y), rgba(c))
    # eye: rows 6..10, columns 28..33
    eye = {
        6: [FACE, RING, RING, FACE, FACE],
        7: [RING, PUPIL, PUPIL, RING, BROWN, BROWN],
        8: [RING, PUPIL, PUPIL, RING, FACE],
        9: [FACE, RING, RING, FACE],
        10: [PALE, PALE, PALE, PALE],
    }
    for y, row in eye.items():
        for i, c in enumerate(row):
            if c:
                put(28 + i, y, c)
    # yellow lore, between beak base and eye
    put(26, 7, YELLOW); put(27, 7, YELLOW); put(27, 8, YELLOW_DK)
    # feet: rufous and stray white pixels on the post top -> pink
    for y in range(46, 53):
        for x in range(34, 49):
            r, g, b, a = im.getpixel((x, y))
            if not a:
                continue
            if (r, g, b) == (0x7b, 0x39, 0x22):
                put(x, y, PINK_DK)
            elif min(r, g, b) > 0xe0:
                put(x, y, PINK)
    im.save(os.path.join(HERE, 'sparrow-1x.png'))
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(os.path.join(ASSETS, 'sparrow.png'))


if __name__ == '__main__':
    main()
