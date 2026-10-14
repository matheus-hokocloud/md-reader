# Domain

Owned by `business-agent`. The shared source of truth for what this software is and why.

## Purpose

Virgilio reads a lot of Markdown (Claude-written `CLAUDE.md`, skills, plans, notes). Opened in
a text editor such as Kate it shows raw syntax, wrapped mid-sentence. Markdown Reader opens a
`.md` file and shows it rendered, comfortably, and nothing else. Started 2026-10-13.

## Users and goals

- One user, on his own CachyOS / KDE Plasma (Wayland) desktop.
- Goal: double-click a `.md` file in Dolphin and read it — no setup, no editing UI in the way.

## Concepts and vocabulary

- **Reader** — the window; one file at a time.
- **Theme** — `light` or `dark`. First run follows the KDE colour scheme; after a toggle the
  choice is remembered.
- **Live reload** — the open file is watched; when it changes on disk the page re-renders in
  place and keeps the scroll position (useful while Claude is still writing the file).
- Supported Markdown: CommonMark + tables + strikethrough, fenced code with syntax
  highlighting, raw HTML, task lists (`- [ ]`/`- [x]`), GitHub alerts (`> [!NOTE]`,
  `TIP`, `IMPORTANT`, `WARNING`, `CAUTION`), YAML front matter shown as a code block.
- Links: `#anchor` scrolls within the page; links to other Markdown (or `.txt`) files open in the reader;
  everything else goes to the desktop default handler (browser, image viewer…).

## Rules and invariants

- **Read-only** (2026-10-13). No editing features "for now" — reading must stay easy and
  simple. Revisit only if Virgilio asks.
- **Dark/light toggle** is a requirement (2026-10-13), always one keystroke away (Ctrl+T).
- **Render properly** (2026-10-13): what GitHub would render, the reader should render, within
  the limits under Open questions.
- Markdown Reader is the default app for `text/markdown` on this machine (installed
  2026-10-13, see `docs/ops.md`).

## Open questions

- Footnotes (`[^1]`) render as plain text: the plugin isn't installed. Install
  `extra/python-mdit_py_plugins` (0.6.1 in the repos) or leave unsupported?
- "We have some work to do yet" (2026-10-13) — next features not yet stated.
