#!/usr/bin/env python3
"""Render a Markdown file in one or more themes and save window screenshots.

Usage: python3 tools/screenshot.py [--theme ID ...] [--width N] [FILE.md] [OUT_DIR]
Defaults: themes light and dark, sample.md, current directory. Writes OUT_DIR/<ID>.png.
`--theme all` renders every available theme. `--width` sets the window width (default 900;
the outline needs about 1080 or more). Themes are switched live (no page reload),
the same path Ctrl+T and the theme menu use.
Runs offscreen with throwaway settings, so the user's saved theme/zoom are untouched.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QSettings, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import mdreader  # noqa: E402

LOAD_MS = 2500
TOGGLE_MS = 800


def main():
    args, themes, width = sys.argv[1:], [], 900
    usage = "usage: screenshot.py [--theme ID|all ...] [--width N] [FILE.md] [OUT_DIR]"
    if "--width" in args:
        i = args.index("--width")
        if i + 1 >= len(args) or not args[i + 1].isdigit():
            sys.exit(usage)
        width = int(args[i + 1])
        del args[i:i + 2]
    while "--theme" in args:
        i = args.index("--theme")
        if i + 1 >= len(args):
            sys.exit(usage)
        themes.append(args[i + 1])
        del args[i:i + 2]
    src = Path(args[0] if args else ROOT / "sample.md").resolve()
    out = Path(args[1] if len(args) > 1 else ".").resolve()
    out.mkdir(parents=True, exist_ok=True)

    settings_dir = tempfile.mkdtemp(prefix="mdreader-shot-")
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, settings_dir)

    app = QApplication(["mdreader-screenshot"])
    win = mdreader.Reader()
    if "all" in themes:
        themes = sorted(win.themes)
    themes = themes or ["light", "dark"]
    missing = [t for t in themes if t not in win.themes]
    if missing:
        sys.exit(f"unknown theme(s): {', '.join(missing)}; available: {', '.join(sorted(win.themes))}")
    win.resize(width, 1000)
    win.open_file(src)
    win.show()

    def step(remaining):
        if not remaining:
            app.quit()
            return
        win.set_theme(remaining[0])

        def grab():
            path = out / f"{win.theme_id}.png"
            win.grab().save(str(path))
            print(path)
            step(remaining[1:])

        QTimer.singleShot(TOGGLE_MS, grab)

    QTimer.singleShot(LOAD_MS, lambda: step(themes))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
