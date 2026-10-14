"""Build the black/white app icon from the hand-drawn masters.

  python3 assets/src/build_icon.py

Masters are text grids (assets/src/icon-32.txt, icon-16.txt):
  '#' black   'w' white   'g' grey   '.' transparent
A 1 px white outline (8-connected) is added around every opaque pixel so the black
bird reads on dark panels as well as light ones.

Outputs: assets/src/icon-{16,32}-master.png (1x, with outline) and
assets/icons/mdreader-{16,32,48,64,128,256}.png + mdreader.png (=256).
48 = 16 x3; 64/128/256 = 32 x2/x4/x8; all nearest-neighbour.
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.dirname(HERE)
COLORS = {'#': (0, 0, 0, 255), 'w': (255, 255, 255, 255), 'g': (128, 128, 128, 255)}
OUTLINE = (255, 255, 255, 255)


def load(name):
    rows = [r.rstrip('\n') for r in open(os.path.join(HERE, name)) if r.strip() and not r.startswith(';')]
    n = len(rows)
    assert all(len(r) == n for r in rows), f'{name}: grid must be {n}x{n}'
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c in COLORS:
                im.putpixel((x, y), COLORS[c])
    # outline: any transparent pixel touching an opaque one (8 neighbours) turns white
    out = im.copy()
    for y in range(n):
        for x in range(n):
            if im.getpixel((x, y))[3]:
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < n and 0 <= yy < n and im.getpixel((xx, yy))[3]:
                        out.putpixel((x, y), OUTLINE)
    return out


def main():
    os.makedirs(os.path.join(ASSETS, 'icons'), exist_ok=True)
    m16, m32 = load('icon-16.txt'), load('icon-32.txt')
    m16.save(os.path.join(HERE, 'icon-16-master.png'))
    m32.save(os.path.join(HERE, 'icon-32-master.png'))
    sizes = {16: (m16, 1), 32: (m32, 1), 48: (m16, 3), 64: (m32, 2), 128: (m32, 4), 256: (m32, 8)}
    for s, (m, k) in sizes.items():
        img = m.resize((m.width * k, m.height * k), Image.NEAREST)
        img.save(os.path.join(ASSETS, 'icons', f'mdreader-{s}.png'))
        if s == 256:
            img.save(os.path.join(ASSETS, 'icons', 'mdreader.png'))


if __name__ == '__main__':
    main()
