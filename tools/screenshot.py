#!/usr/bin/env python3
"""Render a Markdown file in both themes and save window screenshots.

Usage: python3 tools/screenshot.py [FILE.md] [OUT_DIR]
Defaults: sample.md, current directory. Writes OUT_DIR/light.png and OUT_DIR/dark.png.
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
    src = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "sample.md").resolve()
    out = Path(sys.argv[2] if len(sys.argv) > 2 else ".").resolve()
    out.mkdir(parents=True, exist_ok=True)

    settings_dir = tempfile.mkdtemp(prefix="mdreader-shot-")
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, settings_dir)

    app = QApplication(["mdreader-screenshot"])
    win = mdreader.Reader()
    win.resize(900, 1000)
    win.open_file(src)
    win.show()

    def grab_then(next_step):
        path = out / f"{win.theme}.png"
        win.grab().save(str(path))
        print(path)
        next_step()

    def second():
        grab_then(app.quit)

    def first():
        grab_then(lambda: (win.toggle_theme(), QTimer.singleShot(TOGGLE_MS, second)))

    QTimer.singleShot(LOAD_MS, first)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
