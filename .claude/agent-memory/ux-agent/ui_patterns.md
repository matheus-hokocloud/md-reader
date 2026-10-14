---
name: ui-patterns
description: md-reader UI building blocks and how chrome/page colours are derived from themes (outline, frameless title bar, chrome QSS/palette)
metadata:
  type: project
---

UI patterns established 2026-10-14 (outline + themed frameless title bar):

- **Page UI lives in the page**: anything drawn over the document (outline) is HTML/CSS/JS in
  `CSS` / `OUTLINE_JS` / `PAGE` so it picks up the theme's CSS variables for free. Inactive
  rules must only match under an opt-in class (`html.outline-on`) so the default render stays
  pixel-identical — checked by rendering with the pre-change CSS/PAGE and comparing grabs.
- `setTheme` must use classList (not `className =`) or it wipes `outline-on`.
- Outline geometry is computed in JS from `#content`'s computed max-width/padding plus
  `--outline-w/gap/edge` on `:root` (single source; 176/20/12). Threshold 1060 CSS px page
  (= 1080 px window); first-run window 1240×900. Narrow-but-on → transient QToolTip says why.
- Outline labels are CSS `::before { content: attr(data-label) }` + `user-select: none`, so
  Find and Select All skip them (review finding 2026-10-14). Keep any page chrome text out of
  text nodes the same way.
- Text contrast: never use theme `muted` raw for small text (Monokai/Solarized fail AA); use
  `color-mix(fg, bg)` in CSS or `_readable()` in Python.
- **Chrome colours** come from `chrome_colors(theme)` → `chrome_palette()` (app QPalette) +
  `chrome_css()` (app QSS, hex only). Re-applied in `apply_theme` and when the platform theme
  resets the app palette (ApplicationPaletteChange).
- Window-control glyphs are painted (`_window_glyph`), not icon-theme icons, so they follow
  the theme colour regardless of the KDE icon recolouring.
- Frameless resize = 4 px contents margin owned by the QMainWindow + `startSystemResize`;
  toolbar/view get explicit Arrow cursors so they don't inherit resize cursors. Move starts
  on drag threshold (not press) so double-click still maximises.

**Why:** Virgilio wants "easy and simple" and theme-matched everything; see [[domain-open-questions]].
**How to apply:** extend these helpers rather than adding one-off colours/styles.
