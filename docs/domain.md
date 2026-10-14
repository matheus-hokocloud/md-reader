# Domain

Owned by `business-agent`. The shared source of truth for what this software is and why.

## Purpose

Virgilio reads a lot of Markdown (Claude-written `CLAUDE.md`, skills, plans, notes). Opened in
a text editor such as Kate it shows raw syntax, wrapped mid-sentence. Markdown Reader opens a
`.md` file and shows it rendered, comfortably, and nothing else. Started 2026-10-13.

## Users and goals

- One user, on his own CachyOS / KDE Plasma (Wayland) desktop.
- Goal: double-click a `.md` file in Dolphin and read it — no setup, no editing UI in the way.
- Goal (2026-10-14): make the reader feel like his own — his colour themes, a mascot, a
  proper app icon.

## Concepts and vocabulary

- **Reader** — the window; one file at a time.
- **Theme** — a named colour set for the page, defined by a JSON file. Each theme has a
  **kind**, `light` or `dark`. (Until 2026-10-13 "theme" meant just light/dark; those two are
  now the built-in themes `light` "Default Light" and `dark` "Default Dark".)
- **Theme id** — the JSON file name without `.json` (`solarized-dark`). What is remembered in
  settings. The old saved values `light`/`dark` are valid ids, so existing settings carry over.
- **Built-in themes** — ship in the repo under `themes/`: `light`, `dark` (exactly the colours
  of 2026-10-13, still the defaults), `solarized-light`, `solarized-dark`, `monokai` (dark).
- **User themes** — `~/.config/mdreader/themes/*.json`. A user file with a built-in's id
  overrides that built-in.
- **Theme file schema** — `name` (display name), `kind` (`light`|`dark`), `pygments` (a
  Pygments style name, for code blocks), `colors` (the page's CSS variables: `bg`, `fg`,
  `muted`, `border`, `soft`, `code-bg`, `link`, `accent`, `stripe`, `mark`; optionally the
  alert colours `note`, `tip`, `important`, `warning`, `caution`).
- **Theme toggle** — Ctrl+T: jump to the last-used theme of the *other* kind.
- **Live reload** — the open file is watched; when it changes on disk the page re-renders in
  place and keeps the scroll position (useful while Claude is still writing the file). Theme
  files get the same treatment (2026-10-14).
- **Sparrow** — the mascot (2026-10-14). Reference: Virgilio's photo of a grassland sparrow —
  brown streaked plumage, yellow lore (spot before the eye), perched on a post, side profile
  facing left. Rendered as pixel art.
- **About dialog** — the one place the project and its author are described.
- **Outline** (2026-10-14) — the floating section menu in the left page margin listing the
  document's headings. Virgilio's words: "a floating menu on left side that lists the file
  sections".
- **Title bar** (2026-10-14) — the reader's own window frame: a custom title bar merged with
  the toolbar, replacing the OS window decoration. **Native decorations** = the KDE frame,
  kept as a fallback option.
- Supported Markdown: CommonMark + tables + strikethrough, fenced code with syntax
  highlighting, raw HTML, task lists (`- [ ]`/`- [x]`), GitHub alerts (`> [!NOTE]`,
  `TIP`, `IMPORTANT`, `WARNING`, `CAUTION`), YAML front matter shown as a code block.
- Links: `#anchor` scrolls within the page; links to other Markdown (or `.txt`) files open in the reader;
  everything else goes to the desktop default handler (browser, image viewer…).

## Rules and invariants

- **Read-only** (2026-10-13). No editing features "for now" — reading must stay easy and
  simple. Revisit only if Virgilio asks. Theme editing (2026-10-14) does not break this: themes
  are edited in an external text editor; the reader never writes documents and has no
  in-app theme editor.
- **Dark/light toggle** is a requirement (2026-10-13), always one keystroke away (Ctrl+T).
  Kept with custom themes (2026-10-14): Ctrl+T switches to the last-used theme of the other
  kind, initially Default Light ↔ Default Dark.
- **Render properly** (2026-10-13): what GitHub would render, the reader should render, within
  the limits under Open questions.
- Markdown Reader is the default app for `text/markdown` on this machine (installed
  2026-10-13, see `docs/ops.md`).

### Themes (2026-10-14)

- Default Light and Default Dark stay the defaults and look exactly as on 2026-10-13
  (pixel-identical page colours and code highlighting).
- First run (no saved theme) still follows the KDE colour scheme → Default Light or Default
  Dark. The chosen theme is remembered across runs.
- All available themes are listed in a picker in the window; picking one applies it at once.
- A theme file can never crash or blank the reader. Invalid JSON, wrong types, unknown
  `kind`, unknown Pygments style or a malformed colour → that file (or that value) is skipped
  with a warning; missing keys fall back to the default theme of the same kind.
- Colour values are colours only (hex / named / `rgb()` style) — nothing else from a theme
  file reaches the page's CSS.
- Editing the active theme's file re-applies it live, keeping scroll position. A half-saved
  or broken file keeps the last good version on screen.
- If the remembered theme disappears, fall back as on first run.
- "Open themes folder" creates `~/.config/mdreader/themes/` if missing and opens it in the
  desktop file manager. The reader does not write theme files itself (assumption: no
  "copy built-in to user folder" action unless Virgilio asks).

### Mascot, About and icon (2026-10-14)

- Art is pixel art made with the local ComfyUI (SDXL + pixel-art-xl LoRA) in
  `/home/virgilio/claude/PixelArt`.
- About illustration: the sparrow in colour, faithful to the reference photo (assumption —
  he said "a sparrow draw"; only the icon was specified black/white).
- App icon: black/white pixel-art sparrow, side profile; must read at 16 px and on both
  light and dark panels. Used as the window icon and in the `.desktop` entry, replacing
  `text-markdown`.
- About shows (revised by Virgilio 2026-10-14, supersedes the original list), top to bottom: app
  name, sparrow, one-line purpose, author, licence, a clickable **GitHub icon** that opens the repo in
  the browser (no URL text), and the version **at the bottom**. All text centred. Removed: the
  "Mascot" line and the tech-stack / version-list line.
- **Never show Virgilio's email in the app.**
- Applying the icon to the desktop entry means re-running `install.sh` (system state) — ask
  Virgilio first.

### Outline (2026-10-14)

- Floats in the left page margin; lists h1–h3, indented by level, in document order.
- Clicking an entry jumps to that section; the section currently being read is highlighted
  and follows scrolling.
- Coloured by the active theme, and re-coloured when the theme changes.
- Hidden when no file is open or the document has fewer than 2 headings (h1–h3).
- Auto-hides when the window is too narrow for it to sit beside the text — it must never
  cover or squeeze the text. It comes back when there is room again.
- Ctrl+Shift+O toggles it; the on/off choice is remembered across runs. Auto-hide on narrow
  windows applies even when the choice is "on".
- Follows live reload: headings added/removed on disk update the outline.
- Read-only: navigation only — no reordering, renaming or editing of sections.

### Themed window frame (2026-10-14)

- Frameless window; a custom title bar merged with the toolbar: Open, theme toggle, centred
  file title, Find box, menu button, minimise / maximise / close.
- All Qt chrome takes its colours from the active theme: title bar, Find box, menus, About
  dialog, scrollbars outside the page. Changing theme (Ctrl+T, picker, live theme edit)
  re-colours the chrome at once.
- Must keep normal KDE/Wayland window behaviour: drag the title bar to move, double-click to
  maximise/restore, resize from the edges, snapping/tiling — via the compositor
  (`QWindow.startSystemMove` / `startSystemResize`), not by hand-moving the window.
- An option falls back to native KDE decorations; the choice is remembered.
- Existing shortcuts and theme behaviour are unchanged.

## Open questions

- Footnotes (`[^1]`) render as plain text: the plugin isn't installed. Install
  `extra/python-mdit_py_plugins` (0.6.1 in the repos) or leave unsupported?
- **Licence** (2026-10-14): none declared in the repo. Which licence should About show (and
  should a `LICENSE` file be added)? Until decided, About says "No licence declared".
- **Version** (2026-10-14): the app has no version number. Proposed `0.1.0`; Virgilio to
  confirm.
- **Author credit** (2026-10-14): git author is "Matheus Hernandes"; the repo remote is
  `github.com/matheus-hokocloud/md-reader`, while his Tetris repo is under `acca90`. Which
  name and handle should About show? Default until answered: "Matheus Hernandes" + the actual
  remote URL.
- **Chrome colours** (2026-10-14): assumption — derived from the existing theme `colors`
  (`bg`, `fg`, `border`, `soft`, `accent`…), no new theme-file keys. Add optional chrome keys
  only if Virgilio wants separate control.
- **Native-decorations fallback** (2026-10-14): where is the option — menu toggle, settings
  entry, or command-line flag? Assumption: a checkable item in the menu, effective on next
  launch if a live switch is impractical.
- **Outline width / narrow threshold** (2026-10-14): not specified; to be judged by eye
  (ux-agent), screenshots for Virgilio.
- "JSON file as editor" is read as "themes are edited by hand in a JSON file" (assumption).
- "We have some work to do yet" (2026-10-13) — further features not yet stated.
