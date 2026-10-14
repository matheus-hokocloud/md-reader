# Security

Owned by `security-agent`.

## Assets

- The user's files: the reader runs as the user and is the default app for every `.md` file,
  including ones from downloads, archives and cloned repos.

## Threats and attack surface

- **Untrusted Markdown.** Raw HTML is passed through (`html: True` in `mdreader.py`) into
  QtWebEngine with JavaScript on. The page is loaded with the Markdown file's `file://` URL as
  base. Measured defaults (2026-10-13, PySide6 6.12 / qt6-webengine 6.11.2): `JavascriptEnabled=True`,
  `LocalContentCanAccessFileUrls=True`, `LocalContentCanAccessRemoteUrls=False`,
  `JavascriptCanOpenWindows=True`. So a hostile `.md` can run script that may read other local
  files; remote access is off by default. **Not yet assessed or mitigated.**
- **Link clicks** are intercepted: non-Markdown targets go to `QDesktopServices.openUrl`, i.e.
  whatever the desktop maps to that URL or file type.

- **Theme files** (2026-10-14, branch `feat/themes-sparrow`). `themes/*.json` (repo) and
  `~/.config/mdreader/themes/*.json` are parsed at startup and on every watcher event.
  Trust level: written by the user (or anyone who can already write to the repo or
  `~/.config` — which already means code execution via shell rc files), so the threat is
  robustness, not privilege. What reaches where:
  - colour values -> page CSS (`<style id="theme">` via `PAGE.format` and via
    `runJavaScript("setTheme(...)")`, JSON-encoded with `json.dumps`). Guarded by an
    allow-list of keys (`COLOR_KEYS`) and a value regex (hex / `rgb|hsl(...)` with digits
    only / an ASCII colour name accepted by `QColor`). Tested 2026-10-14: `;}`, `</style>`,
    `url()`, `expression`, `inherit` are all rejected; nothing else from the file reaches CSS.
  - `kind` -> CSS selector and QSettings key; only `light`/`dark` accepted.
  - `pygments` -> `HtmlFormatter(style=...)`; must be in `get_all_styles()`, so only
    installed styles load (no arbitrary import path).
  - `name` -> QAction text (plain text, `&` escaped, C0 controls stripped, 60 chars).
    Never reaches HTML.
  - File reads go through `_read_small`: `O_NONBLOCK` open, `fstat` must be a regular file
    (rejects FIFOs and devices, including via symlink), at most 64 KiB + 1 bytes read.
  - Mitigated 2026-10-14 (found by security-agent, fixed by code-agent, verified by
    review-agent): a FIFO named `*.json` hung startup; a symlink to `/dev/zero` raised an
    uncaught `MemoryError`; a growing file could bypass the `stat()` size cap; the colour
    check accepted malformed numbers like `rgb(....,..,..)`. Now FIFO and `/dev/zero` are
    rejected instantly, a 70 KB file is rejected, and `rgb()`/`hsl()` arguments must be
    proper numbers (`_NUM`).
- **About dialog**: the repo link is an icon `QPushButton` (`assets/github.svg`, tinted)
  whose click opens the constant `REPO_URL` via `QDesktopServices.openUrl`. Only if the SVG
  is missing or invalid does it fall back to a rich-text `QLabel` with
  `setOpenExternalLinks(True)` and the same constant URL. No file-derived text in rich text.
- **Outline panel** (2026-10-14): built in page JS from `#content h1-h3`. Heading text (which
  comes from the untrusted Markdown) goes in only via `textContent`, `data-label`,
  `aria-label` and `title` - never `innerHTML`; the link target is always `'#' + h.id`, a
  same-page fragment. Adds no new injection path beyond the untrusted-Markdown item above.
- **Frameless title bar** (2026-10-14): custom window chrome (move/resize via
  `startSystemMove`/`startSystemResize`, window buttons). No new input surface. The file name
  is shown in a `PlainText` `QLabel`. Its full-path tooltip was rich-text injectable (Qt
  auto-detects markup, e.g. a file named `.../<b>x</b>.md`) — mitigated 2026-10-14: the path
  is `html.escape`d inside a `white-space:pre` paragraph, and path-bearing warning dialogs are
  forced to plain text.
- **"Open themes folder"**: `QDesktopServices.openUrl` on `$XDG_CONFIG_HOME/mdreader/themes`
  after `mkdir(exist_ok=True)`, which raises if the path exists as a non-directory, so it
  cannot be used to launch a file. A relative `XDG_CONFIG_HOME` is ignored, per the XDG spec.
- **Page globals** (`render`, `setTheme`, `goto`) live in the page's main world, so script in a
  hostile `.md` can redefine them. Nothing secret is passed to them; informational, part of
  the untrusted-Markdown item above.
- **install.sh icons**: copies fixed-name PNGs from `assets/icons/` into
  `~/.local/share/icons/hicolor/<n>x<n>/apps/`. Paths are quoted or come from fixed values;
  no injection. Changes desktop state — run only with Virgilio's go-ahead.

## Accepted risks

None yet.
