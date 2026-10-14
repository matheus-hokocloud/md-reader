---
name: project-review-setup
description: How to verify md-reader changes when there is no test suite - offscreen harness, pixel compare vs HEAD, isolation pitfalls, recurring bug classes
metadata:
  type: project
---

md-reader has no automated test suite (as of 2026-10-14); review verification is done by
driving `mdreader.Reader` offscreen from a scratch script.

**Why:** domain rules like "Default Light/Dark pixel-identical to 2026-10-13" and "live theme
re-apply keeps scroll" can only be checked by running the app.

**How to apply:**
- Isolate state: `QSettings.setPath(NativeFormat, UserScope, <tmp>)` for settings AND
  `XDG_CONFIG_HOME=<tmp>` for user themes (`user_theme_dir()` reads XDG, QSettings does not).
  `tools/screenshot.py` only isolates QSettings, so export XDG_CONFIG_HOME before running it.
  Virgilio uses `~/.config/mdreader` live - never write there.
- Pixel check of the page: `git archive HEAD | tar -x -C <scratch>/old`, then in both trees
  `win.view.setFixedSize(860, 1400)` and `win.view.grab()` - immune to title-bar/chrome
  height changes (comparing window grabs below y>60 broke once the frameless title bar landed).
- JS round-trip helper: `page.runJavaScript(code, cb)` + QEventLoop; outline state is in the
  page global `outline` (`outline.links`, `layoutOutline()` returns on/off/few/narrow).
- Outline needs viewport >= ~1092 CSS px (820 col + 64 pad + 208); 900-wide screenshots
  never show it - resize to ~1300 to see it.
- Recurring bug classes: (1) `runJavaScript` while `setHtml` is loading is lost - check
  `on_loaded` re-syncs (theme, outline); (2) page-injected UI (outline) leaks into Find and
  Select-All; (3) docs/security.md going stale after fixes.
- docs/security.md staleness recurred on the 3rd pass (fixed items still listed as open) -
  diff every security.md "open"/"not rejected" claim against the code.
- Don't `py_compile` in the repo: it drops `__pycache__/` there (gitignored, but still a
  write). Use `python3 -B` / `PYTHONDONTWRITEBYTECODE=1`, or compile from the scratch copy.
- Offscreen cannot verify `startSystemMove/Resize`, KWin snapping or real icon themes - say so.
