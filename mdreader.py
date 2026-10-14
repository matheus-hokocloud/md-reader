#!/usr/bin/env python3
"""mdreader - a small, read-only Markdown viewer with JSON colour themes.

Usage: mdreader [FILE.md]

Keys: Ctrl+O open · Ctrl+T light/dark theme · Ctrl+F find · Ctrl+R reload
      Ctrl+Shift+O outline · Ctrl+= / Ctrl+- / Ctrl+0 zoom · F1 about · Ctrl+Q quit
Title bar (own frame unless "Use system title bar"): drag to move, double-click to maximise.
Themes: themes/*.json (built-in) and ~/.config/mdreader/themes/*.json (override by id).
The open file and the theme files are watched and re-applied in place when they change.
"""
import html
import json
import os
import re
import stat
import sys
from pathlib import Path

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_all_styles
from pygments.util import ClassNotFound
from PySide6.QtCore import (QEvent, QFileSystemWatcher, QPoint, QPointF, QRect, QRectF, QSettings,
                            QSize, Qt, QTimer, QUrl)
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QFont, QGuiApplication,
                           QIcon, QImage, QKeySequence, QPainter, QPalette, QPen, QPixmap)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QFileDialog,
                               QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton,
                               QSizePolicy, QToolBar, QToolButton, QToolTip, QVBoxLayout,
                               QWidget)

__version__ = "0.1.0"

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
REPO_URL = "https://github.com/matheus-hokocloud/md-reader"
MD_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd", ".mdx", ".txt"}

# --------------------------------------------------------------------------- rendering

_FORMATTER = HtmlFormatter(nowrap=True)


def _highlight(code, lang, _attrs):
    if not lang:
        return ""  # empty -> markdown-it escapes it itself
    try:
        lexer = get_lexer_by_name(lang.split()[0])
    except ClassNotFound:
        return ""
    return highlight(code, lexer, _FORMATTER)


def _heading_ids(state):
    """GitHub-style ids on headings, so #anchor links work."""
    seen = {}
    tokens = state.tokens
    for i, tok in enumerate(tokens):
        if tok.type != "heading_open" or i + 1 >= len(tokens):
            continue
        text = tokens[i + 1].content
        slug = re.sub(r"[^\w\- ]", "", text.lower()).strip().replace(" ", "-")
        slug = slug or "section"  # punctuation/emoji-only headings would get id=""
        n = seen.get(slug, 0)
        seen[slug] = n + 1
        tok.attrSet("id", slug if n == 0 else f"{slug}-{n}")


_md = MarkdownIt("commonmark", {"html": True, "typographer": False, "highlight": _highlight})
_md.enable(["table", "strikethrough"])
_md.core.ruler.push("heading_ids", _heading_ids)

_FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.S)
_TASK = re.compile(r"<li>(<p>)?\[([ xX])\][ \t]")
_ALERT = re.compile(r"<blockquote>\s*<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*", re.I)


def render_markdown(text):
    front = ""
    m = _FRONT_MATTER.match(text)
    if m:
        body = _highlight(m.group(1), "yaml", None)
        front = f'<pre class="frontmatter"><code>{body}</code></pre>\n'
        text = text[m.end():]

    out = _md.render(text)
    out = _TASK.sub(
        lambda m: f'<li class="task">{m[1] or ""}<input type="checkbox" onclick="return false"'
        f'{" checked" if m[2] != " " else ""}> ',
        out,
    )
    out = _ALERT.sub(
        lambda m: f'<blockquote class="alert alert-{m[1].lower()}">'
        f'<p class="alert-title">{m[1].capitalize()}</p><p>',
        out,
    )
    return front + out


# --------------------------------------------------------------------------- themes

KINDS = ("light", "dark")
COLOR_KEYS = ("bg", "fg", "muted", "border", "soft", "code-bg", "link", "accent", "stripe", "mark",
              "alert-note", "alert-tip", "alert-important", "alert-warning", "alert-caution")
_ALERTS = {"note", "tip", "important", "warning", "caution"}  # domain.md spells them bare
_ALERT_COLORS = {"alert-note": "#4493f8", "alert-tip": "#2da44e", "alert-important": "#8957e5",
                 "alert-warning": "#c48a00", "alert-caution": "#d1242f"}
# Last-resort defaults, used if themes/light.json or dark.json are missing or broken.
_FALLBACK = {
    "light": {"id": "light", "name": "Default Light", "kind": "light", "pygments": "default",
              "path": None, "colors": {
                  "bg": "#fbfbfa", "fg": "#1f2328", "muted": "#5d6570", "border": "#d9dde3",
                  "soft": "#f1f3f5", "code-bg": "#f3f4f6", "link": "#0b62d6", "accent": "#0b62d6",
                  "stripe": "#f6f7f9", "mark": "#fff3b0", **_ALERT_COLORS}},
    "dark": {"id": "dark", "name": "Default Dark", "kind": "dark", "pygments": "github-dark",
             "path": None, "colors": {
                 "bg": "#16171a", "fg": "#d9dce1", "muted": "#8c939e", "border": "#30343b",
                 "soft": "#1e2025", "code-bg": "#1d1f24", "link": "#6aa8ff", "accent": "#6aa8ff",
                 "stripe": "#1b1d21", "mark": "#5c4d12", **_ALERT_COLORS}},
}
BUILTIN_THEMES = HERE / "themes"
# Colours only: hex, rgb()/hsl() with numeric arguments, or a CSS/SVG colour name. The
# character classes exclude ; { } ( ) quotes etc., so nothing else can reach the CSS.
_HEX = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})")
_NUM = r"(?:\d+(?:\.\d+)?|\.\d+)"
_FUNC = re.compile(rf"(?:rgba?\( *{_NUM}%?|hsla?\( *{_NUM}(?:deg)?)(?: *[, /] *{_NUM}%?){{2,3}} *\)")
_NAME = re.compile(r"[a-zA-Z]{3,30}")


def user_theme_dir():
    config = os.environ.get("XDG_CONFIG_HOME", "")
    if not os.path.isabs(config):  # unset or relative: ignored, per the XDG spec
        config = str(Path.home() / ".config")
    return Path(config) / "mdreader" / "themes"


def _warn(path, msg):
    print(f"mdreader: theme {path}: {msg}", file=sys.stderr)


def valid_color(value):
    if not isinstance(value, str):
        return False
    v = value.strip()
    if _HEX.fullmatch(v) or _FUNC.fullmatch(v):
        return True
    return bool(_NAME.fullmatch(v)) and QColor.isValidColorName(v)


def _read_small(path, limit=64 * 1024):
    """Regular files only, at most `limit` bytes. O_NONBLOCK so a FIFO can't block the open."""
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as f:
        if not stat.S_ISREG(os.fstat(fd).st_mode):  # FIFOs, devices (incl. via symlink)
            raise ValueError("not a regular file")
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError("file too large")
    return data


def _parse_theme(path, base):
    """One theme file -> theme dict, or None (with a warning) if it is unusable."""
    try:
        data = json.loads(_read_small(path).decode("utf-8"))
    except (OSError, ValueError) as e:  # JSONDecodeError and UnicodeDecodeError are ValueErrors
        _warn(path, f"skipped: {e}")
        return None
    if not isinstance(data, dict):
        _warn(path, "skipped: not a JSON object")
        return None
    kind = data.get("kind")
    if kind not in KINDS:
        _warn(path, f"skipped: kind must be 'light' or 'dark', got {kind!r}")
        return None
    fallback = base[kind]
    name = data.get("name")
    name = " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", name).split())[:60] if isinstance(name, str) else ""
    if not name:
        if "name" in data:
            _warn(path, "bad 'name', using the file name")
        name = path.stem
    style = data.get("pygments", fallback["pygments"])
    if not isinstance(style, str) or style not in set(get_all_styles()):
        _warn(path, f"unknown pygments style {style!r}, using {fallback['pygments']!r}")
        style = fallback["pygments"]
    colors = dict(fallback["colors"])
    raw = data.get("colors", {})
    if not isinstance(raw, dict):
        _warn(path, "'colors' is not an object, using defaults")
        raw = {}
    for key, value in raw.items():
        key = f"alert-{key}" if key in _ALERTS else key
        if key not in COLOR_KEYS:
            _warn(path, f"unknown colour {key!r} ignored")
        elif not valid_color(value):
            _warn(path, f"colour {key!r} is not a colour: {value!r}")
        else:
            colors[key] = value.strip()
    return {"id": path.stem, "name": name, "kind": kind, "pygments": style, "path": str(path),
            "colors": colors}


def load_themes():
    """All themes by id, plus the set of theme files that failed to load.

    `light` and `dark` always exist. Missing keys come from the built-in default of the
    same kind; user themes override built-ins with the same id.
    """
    failed = set()
    base = dict(_FALLBACK)
    for kind in KINDS:
        path = BUILTIN_THEMES / f"{kind}.json"
        if not path.is_file():
            continue
        t = _parse_theme(path, _FALLBACK)
        if t and t["kind"] == kind:
            base[kind] = t
        else:
            failed.add(str(path))
    themes = dict(base)
    for folder in (BUILTIN_THEMES, user_theme_dir()):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.json")):
            if path.name.startswith(".") or (folder == BUILTIN_THEMES and path.stem in KINDS):
                continue
            t = _parse_theme(path, base)
            if t and t["id"] in KINDS and t["kind"] != t["id"]:
                _warn(path, f"skipped: a '{t['id']}' theme must have kind '{t['id']}'")
                t = None
            if t:
                themes[t["id"]] = t
            else:
                failed.add(str(path))
    return themes, failed


def theme_css(theme):
    kind = theme["kind"]
    variables = "; ".join(f"--{k}: {v}" for k, v in theme["colors"].items())
    pyg = HtmlFormatter(style=theme["pygments"]).get_style_defs(f"html.{kind} pre")
    return f"html.{kind} {{ {variables}; }}\n{pyg}"


def theme_qcolor(theme, key):
    """A theme colour as an opaque QColor (alpha dropped), falling back to the kind's default."""
    fallback = _FALLBACK[theme["kind"]]["colors"][key]
    value = theme["colors"].get(key, fallback)
    if value.startswith("#") and len(value) in (5, 9):  # CSS #rgba/#rrggbbaa; QColor reads #argb
        value = value[:{5: 4, 9: 7}[len(value)]]
    c = QColor(value)
    if not c.isValid() and _FUNC.fullmatch(value):  # QColor can't parse rgb()/hsl()
        nums = re.findall(rf"({_NUM})(%?)", value)
        if value.startswith("rgb"):
            c = QColor(*(min(255, round(float(n) * (2.55 if pct else 1))) for n, pct in nums[:3]))
        else:
            h, s, l = (float(n) for n, _ in nums[:3])
            c = QColor.fromHslF((h % 360) / 360, min(s, 100) / 100, min(l, 100) / 100)
    if not c.isValid() or c.alpha() == 0:  # e.g. `transparent`: no colour to keep
        return QColor(fallback)
    c.setAlpha(255)
    return c


def theme_bg(theme):
    return theme_qcolor(theme, "bg")


def _mix(a, b, t):
    """a blended toward b by t (0..1)."""
    return QColor.fromRgbF(*(x + (y - x) * t for x, y in zip(a.getRgbF()[:3], b.getRgbF()[:3])))


def _contrast(a, b):
    def lum(c):
        ch = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c.getRgbF()[:3]]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _readable(color, toward, bg, ratio=4.5):
    """`color`, moved toward `toward` just enough to reach `ratio` against `bg` (WCAG AA text)."""
    for i in range(11):
        c = _mix(color, toward, i / 10)
        if _contrast(c, bg) >= ratio:
            return c
    return QColor(toward)


def chrome_colors(theme):
    """Window chrome colours (title bar, menus, dialogs) derived from the page theme."""
    c = {k: theme_qcolor(theme, k) for k in ("bg", "fg", "muted", "border", "soft", "accent",
                                             "link", "stripe", "alert-caution")}
    c["bar"] = c["soft"]
    c["muted"] = _readable(c["muted"], c["fg"], c["bar"])
    c["hover"] = _mix(c["bar"], c["fg"], 0.10)
    c["pressed"] = _mix(c["bar"], c["fg"], 0.18)
    c["menu-hover"] = _mix(c["bg"], c["accent"], 0.18)
    c["on-accent"] = max((c["bg"], c["fg"]), key=lambda x: _contrast(x, c["accent"]))
    return c


def chrome_palette(c):
    P = QPalette.ColorRole
    pal = QPalette()
    for role, color in ((P.Window, c["bg"]), (P.WindowText, c["fg"]), (P.Base, c["bg"]),
                        (P.AlternateBase, c["stripe"]), (P.Text, c["fg"]), (P.Button, c["soft"]),
                        (P.ButtonText, c["fg"]), (P.BrightText, c["alert-caution"]),
                        (P.Highlight, c["accent"]), (P.HighlightedText, c["on-accent"]),
                        (P.ToolTipBase, c["soft"]), (P.ToolTipText, c["fg"]),
                        (P.PlaceholderText, c["muted"]), (P.Link, c["link"]),
                        (P.LinkVisited, c["link"]), (P.Light, _mix(c["soft"], c["fg"], 0.05)),
                        (P.Midlight, _mix(c["soft"], c["border"], 0.5)), (P.Mid, c["border"]),
                        (P.Dark, _mix(c["border"], c["fg"], 0.25)), (P.Shadow, _mix(c["bg"], QColor("black"), 0.5))):
        pal.setColor(role, color)
    for role in (P.WindowText, P.Text, P.ButtonText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, c["muted"])
    return pal


def chrome_css(c):
    """Qt style sheet for the chrome. Only QColor.name() hex values reach it."""
    h = {k: v.name() for k, v in c.items()}
    return f"""
QToolBar#titlebar {{ background: {h['bar']}; border: none; border-bottom: 1px solid {h['border']};
                     padding: 3px 6px; spacing: 4px; }}
QToolBar#titlebar QToolButton {{ color: {h['fg']}; background: transparent; border: 1px solid transparent;
                                 border-radius: 6px; padding: 4px 8px; }}
QToolBar#titlebar QToolButton:hover {{ background: {h['hover']}; }}
QToolBar#titlebar QToolButton:pressed, QToolBar#titlebar QToolButton:checked {{ background: {h['pressed']}; }}
QToolBar#titlebar QToolButton:focus {{ border-color: {h['accent']}; }}
QToolBar#titlebar QToolButton::menu-indicator {{ image: none; width: 0; }}
QToolBar#titlebar QToolButton#winbtn {{ padding: 4px 10px; }}
QToolBar#titlebar QToolButton#winclose {{ padding: 4px 10px; }}
QToolBar#titlebar QToolButton#winclose:hover {{ background: {h['alert-caution']}; }}
QToolBar#titlebar QLineEdit {{ background: {h['bg']}; color: {h['fg']}; border: 1px solid {h['border']};
                               border-radius: 6px; padding: 3px 6px;
                               selection-background-color: {h['accent']}; selection-color: {h['on-accent']}; }}
QToolBar#titlebar QLineEdit:focus {{ border-color: {h['accent']}; }}
QMenu {{ background: {h['bg']}; color: {h['fg']}; border: 1px solid {h['border']}; padding: 4px; }}
QMenu::item {{ background: transparent; padding: 5px 24px 5px 8px; border-radius: 4px; }}
QMenu::item:selected {{ background: {h['menu-hover']}; color: {h['fg']}; }}
QMenu::item:disabled {{ color: {h['muted']}; }}
QMenu::separator {{ height: 1px; background: {h['border']}; margin: 4px 6px; }}
QToolTip {{ background: {h['soft']}; color: {h['fg']}; border: 1px solid {h['border']}; padding: 3px 6px; }}
"""


def _window_glyph(kind, color, dpr):
    """Minimise / maximise / restore / close glyph, 16 px, drawn in the theme's colour."""
    px = round(16 * dpr)
    pix = QPixmap(px, px)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.scale(dpr, dpr)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, kind == "close")
    p.setPen(QPen(color, 1.2 if kind == "close" else 1.0))
    if kind == "minimize":
        p.drawLine(QPointF(3.5, 8.5), QPointF(12.5, 8.5))
    elif kind == "maximize":
        p.drawRect(QRectF(3.5, 3.5, 9, 9))
    elif kind == "restore":
        p.drawRect(QRectF(3.5, 5.5, 7, 7))
        p.drawPolyline([QPointF(5.5, 5.5), QPointF(5.5, 3.5), QPointF(12.5, 3.5),
                        QPointF(12.5, 10.5), QPointF(10.5, 10.5)])
    else:
        p.drawLine(QPointF(4, 4), QPointF(12, 12))
        p.drawLine(QPointF(12, 4), QPointF(4, 12))
    p.end()
    pix.setDevicePixelRatio(dpr)
    return pix


CSS = """
:root { color-scheme: light; }
html.dark { color-scheme: dark; }
html, body { background: var(--bg); color: var(--fg); margin: 0; }
body {
  font-family: "Inter", "Noto Sans", "Fira Sans", system-ui, sans-serif;
  font-size: 16.5px; line-height: 1.68;
  -webkit-font-smoothing: antialiased;
}
#content { max-width: 820px; margin: 0 auto; padding: 48px 32px 120px; }
#content > :first-child { margin-top: 0; }

h1, h2, h3, h4, h5, h6 { line-height: 1.25; margin: 1.8em 0 0.6em; font-weight: 650; scroll-margin-top: 16px; }
h1 { font-size: 2em; padding-bottom: .3em; border-bottom: 1px solid var(--border); }
h2 { font-size: 1.5em; padding-bottom: .25em; border-bottom: 1px solid var(--border); }
h3 { font-size: 1.25em; }
h4 { font-size: 1.05em; }
h5, h6 { font-size: .95em; color: var(--muted); }
p, ul, ol, table, pre, blockquote { margin: 0 0 1.1em; }
ul, ol { padding-left: 1.7em; }
li + li, li > ul, li > ol { margin-top: .3em; }
li > p { margin-bottom: .4em; }
li.task { list-style: none; margin-left: -1.4em; }
li.task input { margin: 0 .5em 0 0; vertical-align: -1px; accent-color: var(--accent); }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
strong { font-weight: 650; }
hr { border: 0; border-top: 1px solid var(--border); margin: 2em 0; }
img { max-width: 100%; border-radius: 4px; }
mark { background: var(--mark); color: inherit; }

code, pre, kbd {
  font-family: "JetBrains Mono", "Hack", "Fira Code", "Noto Sans Mono", monospace;
  font-size: .87em;
}
:not(pre) > code {
  background: var(--code-bg); border: 1px solid var(--border);
  padding: .1em .38em; border-radius: 5px; overflow-wrap: anywhere;
}
html pre {
  background: var(--code-bg) !important; border: 1px solid var(--border);
  border-radius: 8px; padding: 14px 18px; overflow-x: auto; line-height: 1.5;
}
pre code { font-size: .92em; }
pre.frontmatter { border-style: dashed; font-size: .95em; }
kbd {
  border: 1px solid var(--border); border-bottom-width: 2px; border-radius: 4px;
  padding: .05em .4em; background: var(--soft);
}

blockquote {
  margin-left: 0; padding: .2em 1em; color: var(--muted);
  border-left: 4px solid var(--border);
}
blockquote > :last-child { margin-bottom: 0; }
blockquote.alert { color: var(--fg); border-left-color: var(--alert); background: var(--soft); border-radius: 0 6px 6px 0; padding: .6em 1em; }
.alert-title { font-weight: 650; color: var(--alert); margin-bottom: .3em; }
.alert-note { --alert: var(--alert-note); }
.alert-tip { --alert: var(--alert-tip); }
.alert-important { --alert: var(--alert-important); }
.alert-warning { --alert: var(--alert-warning); }
.alert-caution { --alert: var(--alert-caution); }

table { border-collapse: collapse; display: block; overflow-x: auto; max-width: 100%; }
th, td { border: 1px solid var(--border); padding: 6px 13px; text-align: left; vertical-align: top; }
th { background: var(--soft); font-weight: 650; }
tbody tr:nth-child(even) { background: var(--stripe); }

.empty { color: var(--muted); text-align: center; margin-top: 30vh; }
.empty b { color: var(--fg); }
::selection { background: color-mix(in srgb, var(--accent) 30%, transparent); }
::-webkit-scrollbar { width: 12px; height: 12px; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 6px; border: 3px solid var(--bg); }
::-webkit-scrollbar-track { background: var(--bg); }

/* Outline: fixed in the left margin. Only shown under html.outline-on, which the script sets
   when the margin is wide enough; otherwise nothing below changes the page. */
:root { --outline-w: 176px; --outline-gap: 20px; --outline-edge: 12px; }
#outline {
  display: none; position: fixed; top: 48px; width: var(--outline-w); box-sizing: border-box;
  max-height: calc(100vh - 96px); overflow-y: auto; overscroll-behavior: contain;
  font-size: 13.5px; line-height: 1.4; user-select: none;  /* not part of the text: no find/copy */
}
html.outline-on #outline { display: block; }
.outline-title::before { content: "Outline"; }
.outline-title {
  margin: 0 0 6px; padding-left: 12px; font-size: 11.5px; font-weight: 650;
  letter-spacing: .06em; text-transform: uppercase;
  color: color-mix(in srgb, var(--fg) 70%, var(--bg));
}
#outline ul { list-style: none; margin: 0; padding: 0; border-left: 1px solid var(--border); }
#outline li + li { margin: 0; }
#outline a {
  display: block; margin-left: -1px; padding: 3px 8px 3px 12px;
  border-left: 2px solid transparent; border-radius: 0 4px 4px 0;
  color: color-mix(in srgb, var(--fg) 78%, var(--bg));
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
#outline a::before { content: attr(data-label); }  /* not a text node, so findText skips it */
#outline a.lvl1 { padding-left: 24px; }
#outline a.lvl2 { padding-left: 36px; }
#outline a:hover { color: var(--fg); background: var(--soft); text-decoration: none; }
#outline a.active { color: var(--fg); font-weight: 650; border-left-color: var(--accent); }
#outline a:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
#outline::-webkit-scrollbar { width: 8px; }
#outline::-webkit-scrollbar-thumb { border-width: 2px; }
#content [tabindex="-1"]:focus { outline: none; }
"""

# The outline (h1-h3 of the document). Heading text goes in with textContent only. Layout is
# computed from #content's own max-width/padding, so the text column never narrows: the
# outline appears beside it when the margin fits, the column shifts right when that makes
# room, and otherwise the outline stays hidden.
OUTLINE_JS = """
const outline = {enabled: true, heads: [], links: [], active: -1, pin: -1, pinUntil: 0, raf: 0};

function layoutOutline() {
  const html = document.documentElement, nav = document.getElementById('outline');
  const content = document.getElementById('content');
  let on = false, margin = '', left = 0;
  if (outline.enabled && outline.heads.length >= 2) {
    const px = v => parseFloat(v) || 0;
    const root = getComputedStyle(html), cs = getComputedStyle(content);
    const w = px(root.getPropertyValue('--outline-w')), gap = px(root.getPropertyValue('--outline-gap'));
    const edge = px(root.getPropertyValue('--outline-edge'));
    const padL = px(cs.paddingLeft), padR = px(cs.paddingRight), col = px(cs.maxWidth);
    const vw = html.clientWidth;
    const centred = (vw - col - padL - padR) / 2;   // margin-left of the centred column
    const need = edge + w + gap - padL;             // smallest margin-left that leaves room
    if (centred >= need) {
      on = true; left = centred + padL - gap - w;
    } else if (need + padL + col + padR <= vw) {
      on = true; margin = need + 'px'; left = edge;
    }
  }
  content.style.marginLeft = margin;
  nav.style.left = on ? left + 'px' : '';
  html.classList.toggle('outline-on', on);
  return on ? 'on' : !outline.enabled ? 'off' : outline.heads.length < 2 ? 'few' : 'narrow';
}

function buildOutline() {
  const list = document.querySelector('#outline ul');
  list.replaceChildren();
  const heads = Array.from(document.querySelectorAll('#content h1, #content h2, #content h3'))
    .filter(h => h.id && h.textContent.trim());
  const top = Math.min(...heads.map(h => +h.tagName[1]));
  outline.heads = heads;
  outline.links = heads.map((h, i) => {
    const text = h.textContent.replace(/\\s+/g, ' ').trim();
    const li = document.createElement('li'), a = document.createElement('a');
    a.href = '#' + h.id;
    a.dataset.label = text;   // shown by CSS ::before; attributes only, never markup
    a.setAttribute('aria-label', text);
    a.title = text;
    a.className = 'lvl' + (+h.tagName[1] - top);
    a.addEventListener('click', e => { e.preventDefault(); jumpTo(i); });
    li.append(a);
    list.append(li);
    return a;
  });
  outline.active = -1;
  outline.pin = -1;
  layoutOutline();
  spy();
}

function setActive(i) {
  if (i === outline.active) return;
  const old = outline.links[outline.active];
  if (old) { old.classList.remove('active'); old.removeAttribute('aria-current'); }
  outline.active = i;
  const a = outline.links[i];
  if (!a) return;
  a.classList.add('active');
  a.setAttribute('aria-current', 'location');
  const nav = document.getElementById('outline');   // keep it visible in a long outline
  if (!document.documentElement.classList.contains('outline-on')) return;
  const nr = nav.getBoundingClientRect(), ar = a.getBoundingClientRect();
  if (ar.top < nr.top) nav.scrollTop -= nr.top - ar.top + 8;
  else if (ar.bottom > nr.bottom) nav.scrollTop += ar.bottom - nr.bottom + 8;
}

function spy() {
  outline.raf = 0;
  const heads = outline.heads;
  if (!heads.length) return setActive(-1);
  if (outline.pin >= 0) {   // a clicked entry stays current while its heading is on screen
    const r = heads[outline.pin].getBoundingClientRect();
    if (performance.now() < outline.pinUntil || (r.top >= 0 && r.top < innerHeight)) return setActive(outline.pin);
    outline.pin = -1;
  }
  const html = document.documentElement;
  const atEnd = scrollY > 0 && scrollY + innerHeight >= html.scrollHeight - 2;
  const line = atEnd ? innerHeight - 1 : Math.min(120, innerHeight * 0.25);
  let idx = -1;
  for (let i = 0; i < heads.length; i++) {
    if (heads[i].getBoundingClientRect().top <= line) idx = i; else break;
  }
  setActive(Math.max(idx, 0));   // above the first heading: the first section is next
}

function jumpTo(i) {
  const h = outline.heads[i];
  if (!h) return;
  outline.pin = i;
  outline.pinUntil = performance.now() + 1200;
  setActive(i);
  const smooth = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  h.scrollIntoView({behavior: smooth ? 'smooth' : 'auto', block: 'start'});
  h.setAttribute('tabindex', '-1');   // keyboard users continue reading from the heading
  h.focus({preventScroll: true});
}

function setOutline(on) { outline.enabled = !!on; const s = layoutOutline(); spy(); return s; }

addEventListener('scroll', () => { if (!outline.raf) outline.raf = requestAnimationFrame(spy); }, {passive: true});
addEventListener('resize', () => { layoutOutline(); spy(); });
for (const t of ['wheel', 'keydown', 'mousedown', 'touchstart'])
  addEventListener(t, () => { if (performance.now() > outline.pinUntil) outline.pin = -1; }, {passive: true});
"""

PAGE = """<!doctype html>
<html class="{kind}"><head><meta charset="utf-8">
<style id="theme">{theme}</style><style>{css}</style>
<script>
function render(html) {{ document.getElementById('content').innerHTML = html; buildOutline(); }}
function setTheme(kind, css) {{
  document.getElementById('theme').textContent = css;
  document.documentElement.classList.remove('light', 'dark');  // keeps outline-on
  document.documentElement.classList.add(kind);
}}
function goto(id) {{ const el = document.getElementById(id); if (el) el.scrollIntoView(); }}
{outline_js}
</script></head>
<body><article id="content">{body}</article>
<nav id="outline" aria-label="Outline"><p class="outline-title" aria-hidden="true"></p><ul></ul></nav>
</body></html>"""

EMPTY = ('<div class="empty"><p><b>No file open</b></p>'
         "<p>Press Ctrl+O, or drop a Markdown file on this window.</p></div>")

# --------------------------------------------------------------------------- window


def app_icon():
    icon = QIcon()
    for n in (16, 32, 48, 64, 128, 256):
        path = ASSETS / "icons" / f"mdreader-{n}.png"
        if path.is_file():
            icon.addFile(str(path), QSize(n, n))
    if (ASSETS / "icons" / "mdreader.png").is_file():
        icon.addFile(str(ASSETS / "icons" / "mdreader.png"))
    return icon if not icon.isNull() else QIcon.fromTheme("text-markdown")


class AboutDialog(QDialog):
    ART_PX = 256  # target size of the illustration's longer side
    GITHUB_PX = 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Markdown Reader")
        self.setModal(True)
        center = Qt.AlignmentFlag.AlignHCenter
        box = QVBoxLayout(self)
        box.setSpacing(10)

        def text(line, scale=1.0, bold=False, muted=False):
            label = QLabel(line, self)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            font = QFont(label.font())
            font.setPointSizeF(font.pointSizeF() * scale)
            font.setBold(bold)
            label.setFont(font)
            if muted:
                label.setForegroundRole(QPalette.ColorRole.PlaceholderText)  # muted in light and dark
            box.addWidget(label)
            return label

        text("Markdown Reader", 1.6, bold=True)

        art = QPixmap(str(ASSETS / "sparrow.png"))
        if not art.isNull():
            # Pixel art: integer factors only, nearest-neighbour, drawn 1:1 on device pixels.
            dpr = self.devicePixelRatioF()
            side, target = max(art.width(), art.height()), int(self.ART_PX * dpr)
            w, h = art.width(), art.height()
            if side <= target:
                w, h = w * (target // side), h * (target // side)
            else:
                f = -(-side // target)
                w, h = w // f, h // f
            art = art.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.FastTransformation)
            art.setDevicePixelRatio(dpr)
            label = QLabel(self)
            label.setPixmap(art)
            box.addWidget(label, 0, center)

        text("A small, read-only Markdown viewer: open a file, read it rendered.")
        text("Author: Matheus Hernandes")
        box.addWidget(self._repo_link(), 0, center)
        text("No licence declared", muted=True)
        box.addSpacing(8)
        text(f"Version {__version__}", 0.9, muted=True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.setCenterButtons(True)
        buttons.rejected.connect(self.reject)
        close = buttons.button(QDialogButtonBox.StandardButton.Close)
        close.setDefault(True)  # Enter closes unless the GitHub button has focus
        box.addWidget(buttons)
        self.setMinimumWidth(480)
        close.setFocus()

    def _repo_link(self):
        self._github = QSvgRenderer(str(ASSETS / "github.svg"))
        if not self._github.isValid():  # no icon: plain text link
            self._github = None
            link = QLabel(f'<a href="{REPO_URL}">{REPO_URL}</a>', self)
            link.setTextFormat(Qt.TextFormat.RichText)
            link.setOpenExternalLinks(True)
            return link
        self._github_button = button = QPushButton(self)
        self._tint_github()
        button.setIconSize(QSize(self.GITHUB_PX, self.GITHUB_PX))
        button.setFlat(True)
        button.setToolTip(REPO_URL)
        button.setAccessibleName("Open the project on GitHub")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO_URL)))
        return button

    def _tint_github(self):
        """Monochrome mark, tinted with the palette's text colour so it shows on light and dark."""
        dpr = self.devicePixelRatioF()
        px = round(self.GITHUB_PX * dpr)
        img = QImage(px, px, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        self._github.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(img.rect(), self.palette().color(QPalette.ColorRole.WindowText))
        painter.end()
        img.setDevicePixelRatio(dpr)
        self._github_button.setIcon(QIcon(QPixmap.fromImage(img)))

    def changeEvent(self, event):
        if event.type() == event.Type.PaletteChange and getattr(self, "_github", None):
            self._tint_github()  # light/dark switched while the dialog is open
        super().changeEvent(event)


class Page(QWebEnginePage):
    def __init__(self, on_link, parent=None):
        super().__init__(parent)
        self._on_link = on_link

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            self._on_link(url)
            return False
        return True


class Reader(QMainWindow):
    RESIZE_MARGIN = 4    # px of window edge that resizes (frameless, not maximised)
    RESIZE_CORNER = 16   # px along an edge, from a corner, that resizes diagonally

    def __init__(self):
        super().__init__()
        self.settings = QSettings("mdreader", "mdreader")
        self.path = None
        self.pending_anchor = None
        self._drag_from = None
        self._chrome_window = None  # app palette Window colour we last set
        # Read once: switching frames takes effect on the next launch (see the menu text).
        self.frameless = not self.settings.value("native_frame", False, type=bool)
        if self.frameless:
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            self.setMouseTracking(True)  # resize cursors over the edge margin

        self.setWindowIcon(app_icon())

        self.themes, _ = load_themes()
        theme_id = self.settings.value("theme")  # old values light/dark are valid ids
        if theme_id not in self.themes:  # first run, or the remembered theme is gone
            dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
            theme_id = "dark" if dark else "light"
        self.theme_id, self.theme = theme_id, self.themes[theme_id]

        self.view = QWebEngineView(self)
        self.view.setAcceptDrops(False)
        self.page = Page(self.on_link, self.view)
        self.page.setBackgroundColor(theme_bg(self.theme))
        self.view.setPage(self.page)
        self.view.loadFinished.connect(self.on_loaded)
        self.view.setZoomFactor(float(self.settings.value("zoom", 1.0)))
        self.view.setCursor(Qt.CursorShape.ArrowCursor)  # don't inherit the window's resize cursors
        self.setCentralWidget(self.view)
        self.setAcceptDrops(True)

        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(lambda _: self.reload_timer.start())
        self.reload_timer = QTimer(self, singleShot=True, interval=150)
        self.reload_timer.timeout.connect(self.reload)

        # Theme files: same debounce, rescan everything on any change.
        self.theme_watcher = QFileSystemWatcher(self)
        self.theme_watcher.fileChanged.connect(lambda _: self.theme_timer.start())
        self.theme_watcher.directoryChanged.connect(lambda _: self.theme_timer.start())
        self.theme_timer = QTimer(self, singleShot=True, interval=150)
        self.theme_timer.timeout.connect(self.rescan_themes)
        self._watch_themes()

        self._build_toolbar()
        self.apply_chrome()
        self._update_frame()
        self.load_page(EMPTY, QUrl())

        geom = self.settings.value("geometry")
        if geom is not None:
            self.restoreGeometry(geom)
        else:
            self.resize(1240, 900)  # first run: wide enough for the outline
        self._update_title()
        self._fit_min_width()
        self.view.setFocus()  # not the Find box: PgDn/Space should scroll from the start

    # ---- UI

    def _build_toolbar(self):
        # Doubles as the title bar when frameless: drag empty space to move, double-click to
        # maximise; the file name is drawn centred over it (see _place_title).
        self.tb = tb = QToolBar("Main", self)
        tb.setObjectName("titlebar")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        tb.setCursor(Qt.CursorShape.ArrowCursor)  # don't inherit the window's resize cursors
        self.addToolBar(tb)

        def action(text, icon, shortcut, slot, add=True):
            a = QAction(QIcon.fromTheme(icon), text, self)
            a.setShortcuts(shortcut if isinstance(shortcut, list) else [shortcut])
            a.triggered.connect(slot)
            self.addAction(a)
            if add:
                tb.addAction(a)
            return a

        action("Open", "document-open", QKeySequence.StandardKey.Open, self.choose_file)
        self.theme_action = action("", "", QKeySequence("Ctrl+T"), self.toggle_theme)
        action("Reload", "view-refresh", [QKeySequence("Ctrl+R"), QKeySequence("F5")], self.reload, add=False)
        action("Zoom in", "", [QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")], lambda: self.zoom(0.1), add=False)
        action("Zoom out", "", QKeySequence("Ctrl+-"), lambda: self.zoom(-0.1), add=False)
        action("Reset zoom", "", QKeySequence("Ctrl+0"), lambda: self.zoom(None), add=False)
        action("Find", "", QKeySequence.StandardKey.Find, self.start_find, add=False)
        action("Quit", "", QKeySequence.StandardKey.Quit, self.close, add=False)
        about = action("About Markdown Reader", "help-about", QKeySequence("F1"), self.show_about, add=False)
        self.outline_action = action("Show outline", "view-list-tree", QKeySequence("Ctrl+Shift+O"),
                                     self.toggle_outline, add=False)
        self.outline_action.setCheckable(True)
        self.outline_action.setChecked(self.settings.value("outline", True, type=bool))
        self._update_theme_action()

        self.find_box = QLineEdit(self)
        self.find_box.setPlaceholderText("Find (Ctrl+F)")
        self.find_box.setAccessibleName("Find in document")
        self.find_box.setClearButtonEnabled(True)
        self.find_box.setMaximumWidth(260)
        self.find_box.textChanged.connect(lambda t: self.view.findText(t))
        self.find_box.returnPressed.connect(self.find_next)
        self.find_box.installEventFilter(self)
        stretch = QWidget(self)
        stretch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(stretch)
        tb.addWidget(self.find_box)

        menu = QMenu(self)
        self.theme_menu = menu.addMenu(QIcon.fromTheme("color-management"), "Theme")
        self.theme_menu.aboutToShow.connect(self.rescan_themes)  # catches dirs created outside the app
        menu.addAction(QIcon.fromTheme("folder-open"), "Open themes folder", self.open_themes_folder)
        menu.addSeparator()
        menu.addAction(self.outline_action)
        frame = menu.addAction("Use system title bar (after restart)")
        frame.setCheckable(True)
        frame.setChecked(not self.frameless)
        frame.setToolTip("Takes effect the next time Markdown Reader starts")
        frame.toggled.connect(lambda on: self.settings.setValue("native_frame", on))
        menu.addSeparator()
        menu.addAction(about)
        button = QToolButton(self)
        button.setIcon(QIcon.fromTheme("application-menu", QIcon.fromTheme("open-menu")))
        button.setText("Menu")  # shown only if the icon theme has neither icon
        button.setToolTip("Menu")
        button.setAccessibleName("Menu")
        button.setAutoRaise(True)
        button.setIconSize(tb.iconSize())
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setMenu(menu)
        tb.addWidget(button)
        self._build_theme_menu()

        self.title_label = QLabel(tb)
        self.title_label.setTextFormat(Qt.TextFormat.PlainText)
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(self.title_label.font())
        font.setWeight(QFont.Weight.DemiBold)
        self.title_label.setFont(font)
        self.title_label.setVisible(self.frameless)  # native frames show the title themselves

        self.window_buttons = {}
        if self.frameless:
            gap = QWidget(self)
            gap.setFixedWidth(8)
            tb.addWidget(gap)
            for kind, tip, slot in (("minimize", "Minimise", self.showMinimized),
                                    ("maximize", "Maximise", self.toggle_maximized),
                                    ("close", "Close", self.close)):
                b = QToolButton(self)
                b.setObjectName("winclose" if kind == "close" else "winbtn")
                b.setToolTip(tip)
                b.setAccessibleName(tip)
                b.setAutoRaise(True)
                b.setIconSize(QSize(16, 16))
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # keyboard: Ctrl+Q, KWin's own shortcuts
                b.clicked.connect(slot)
                tb.addWidget(b)
                self.window_buttons[kind] = b
        tb.installEventFilter(self)  # last: the filter uses the widgets above

    def _build_theme_menu(self):
        self.theme_menu.clear()
        if getattr(self, "theme_group", None):
            self.theme_group.deleteLater()
        self.theme_group = group = QActionGroup(self.theme_menu)
        for kind in KINDS:
            self.theme_menu.addSection(kind.capitalize())
            for t in sorted((t for t in self.themes.values() if t["kind"] == kind),
                            key=lambda t: t["name"].casefold()):
                a = self.theme_menu.addAction(t["name"].replace("&", "&&"))  # plain text, no mnemonic
                a.setCheckable(True)
                a.setData(t["id"])
                a.setChecked(t["id"] == self.theme_id)
                a.triggered.connect(lambda _=False, i=t["id"]: self.set_theme(i))
                group.addAction(a)

    def _update_theme_action(self):
        if self.theme["kind"] == "dark":
            self.theme_action.setText("Light mode")
            self.theme_action.setIcon(QIcon.fromTheme("weather-clear"))
        else:
            self.theme_action.setText("Dark mode")
            self.theme_action.setIcon(QIcon.fromTheme("weather-clear-night"))
        self.theme_action.setToolTip(f"{self.theme_action.text()} (Ctrl+T)")

    def _update_title(self):
        name = self.path.name if self.path else "Markdown Reader"
        self.setWindowTitle(f"{name} — Markdown Reader" if self.path else name)
        # Tooltips auto-detect rich text: escape, so a file named <img src=…>.md stays text.
        tip = f'<p style="white-space:pre">{html.escape(str(self.path))}</p>' if self.path else ""
        self.title_label.setToolTip(tip)
        self._place_title()

    def _place_title(self):
        """Centre the file name on the title bar, elided to the room between the groups."""
        if not self.frameless:
            return
        tb, label = self.tb, self.title_label
        left_w = tb.widgetForAction(self.theme_action)
        left = left_w.geometry().right() + 12 if left_w and left_w.isVisible() else 12
        right = self.find_box.geometry().left() - 12 if self.find_box.isVisible() else tb.width() - 12
        name = self.path.name if self.path else "Markdown Reader"
        fm = label.fontMetrics()
        centre = tb.width() // 2
        half = min(centre - left, right - centre)
        if 2 * half < fm.horizontalAdvance(name):  # no room on the window's centre line:
            centre, half = (left + right) // 2, (right - left) // 2  # centre between the groups
        half = max(0, half)
        text = fm.elidedText(name, Qt.TextElideMode.ElideMiddle, 2 * half)
        label.setText(text)
        label.setGeometry(centre - half, 0, 2 * half, tb.height())
        label.setVisible(bool(text))

    # ---- window frame (frameless mode)

    def apply_chrome(self):
        """Colour all Qt chrome (title bar, menus, dialogs, tooltips) from the active theme."""
        c = self._chrome = chrome_colors(self.theme)
        app = QApplication.instance()
        self._chrome_window = c["bg"]
        app.setPalette(chrome_palette(c))
        app.setStyleSheet(chrome_css(c))
        title = QPalette(self.title_label.palette())
        title.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.WindowText, c["fg"])
        title.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.WindowText, c["muted"])
        self.title_label.setPalette(title)
        self._update_window_buttons()
        self.update()

    def _update_window_buttons(self):
        if not self.window_buttons:
            return
        dpr = self.devicePixelRatioF()
        fg = self._chrome["fg"]
        on_red = max((QColor("white"), QColor("black")),
                     key=lambda x: _contrast(x, self._chrome["alert-caution"]))
        maxed = self.isMaximized()
        for kind, b in self.window_buttons.items():
            glyph = "restore" if kind == "maximize" and maxed else kind
            icon = QIcon(_window_glyph(glyph, fg, dpr))
            if kind == "close":  # glyph stays readable on the red hover background
                icon.addPixmap(_window_glyph(glyph, on_red, dpr), QIcon.Mode.Active)
            b.setIcon(icon)
        tip = "Restore" if maxed else "Maximise"
        self.window_buttons["maximize"].setToolTip(tip)
        self.window_buttons["maximize"].setAccessibleName(tip)

    def _update_frame(self):
        """Resize margins (and the 1 px border) only when frameless and not maximised."""
        edge = self.frameless and not (self.isMaximized() or self.isFullScreen())
        m = self.RESIZE_MARGIN if edge else 0
        self.setContentsMargins(m, m, m, m)
        if not edge:
            self.unsetCursor()
        self._update_window_buttons()
        self.update()

    def toggle_maximized(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def _edges_at(self, pos):
        if not self.frameless or self.isMaximized() or self.isFullScreen():
            return Qt.Edge(0)
        m, c, w, h = self.RESIZE_MARGIN, self.RESIZE_CORNER, self.width(), self.height()
        x, y = pos.x(), pos.y()
        left, right, top, bottom = x < m, x >= w - m, y < m, y >= h - m
        if left or right:
            top, bottom = top or y < c, bottom or y >= h - c
        if top or bottom:
            left, right = left or x < c, right or x >= w - c
        edges = Qt.Edge(0)
        for on, e in ((left, Qt.Edge.LeftEdge), (right, Qt.Edge.RightEdge),
                      (top, Qt.Edge.TopEdge), (bottom, Qt.Edge.BottomEdge)):
            if on:
                edges |= e
        return edges

    _CURSORS = {
        Qt.Edge.LeftEdge: Qt.CursorShape.SizeHorCursor, Qt.Edge.RightEdge: Qt.CursorShape.SizeHorCursor,
        Qt.Edge.TopEdge: Qt.CursorShape.SizeVerCursor, Qt.Edge.BottomEdge: Qt.CursorShape.SizeVerCursor,
        Qt.Edge.LeftEdge | Qt.Edge.TopEdge: Qt.CursorShape.SizeFDiagCursor,
        Qt.Edge.RightEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeFDiagCursor,
        Qt.Edge.RightEdge | Qt.Edge.TopEdge: Qt.CursorShape.SizeBDiagCursor,
        Qt.Edge.LeftEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeBDiagCursor,
    }

    def mouseMoveEvent(self, event):
        shape = self._CURSORS.get(self._edges_at(event.position().toPoint()))
        if shape is None:
            self.unsetCursor()
        else:
            self.setCursor(shape)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        edges = self._edges_at(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and edges != Qt.Edge(0):
            self.windowHandle().startSystemResize(edges)  # compositor-driven: snapping keeps working
            event.accept()
            return
        super().mousePressEvent(event)

    def leaveEvent(self, event):
        self.unsetCursor()
        super().leaveEvent(event)

    def paintEvent(self, event):
        if not (self.frameless and self.contentsMargins().top()):
            return super().paintEvent(event)
        p = QPainter(self)
        p.fillRect(self.rect(), self._chrome["bg"])
        p.fillRect(QRect(0, 0, self.width(), self.RESIZE_MARGIN), self._chrome["bar"])  # above the bar
        p.setPen(self._chrome["border"])
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        p.end()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            self._update_frame()
        elif event.type() == QEvent.Type.ApplicationPaletteChange and self._chrome_window is not None:
            # The platform theme resets the app palette when the KDE colour scheme changes.
            if QApplication.palette().color(QPalette.ColorRole.Window) != self._chrome_window:
                QTimer.singleShot(0, self.apply_chrome)
        super().changeEvent(event)

    def createPopupMenu(self):
        return None  # no right-click "hide toolbar": it is the title bar

    # ---- page loading

    def load_page(self, body, base_url):
        self._pending_body = body
        # Content is injected after load: setHtml caps at 2 MB, runJavaScript doesn't.
        html = PAGE.format(kind=self.theme["kind"], theme=theme_css(self.theme), css=CSS, body="",
                           outline_js=OUTLINE_JS)
        self.view.setHtml(html, base_url)

    def on_loaded(self, ok):
        if ok and self._pending_body is not None:
            # The theme may have changed while loading; setTheme then hit the old document.
            self.page.runJavaScript(self._theme_js())
            self.page.runJavaScript(f"setOutline({json.dumps(self.outline_action.isChecked())})")
            self.inject(self._pending_body)
            self._pending_body = None
            if self.pending_anchor:
                self.page.runJavaScript(f"goto({json.dumps(self.pending_anchor)})")
                self.pending_anchor = None

    def inject(self, body):
        self.page.runJavaScript(f"render({json.dumps(body)})")

    def read_rendered(self):
        text = self.path.read_text(encoding="utf-8", errors="replace")
        return render_markdown(text)

    def open_file(self, path, anchor=None):
        path = Path(path).expanduser().resolve()
        try:
            body = render_markdown(path.read_text(encoding="utf-8", errors="replace"))
        except OSError as e:
            self._warn_box(f"Could not open {path}:\n{e}")
            return
        if self.watcher.files():
            self.watcher.removePaths(self.watcher.files())
        self.path = path
        self.watcher.addPath(str(path))
        self.pending_anchor = anchor
        self.settings.setValue("last_dir", str(path.parent))
        self.load_page(body, QUrl.fromLocalFile(str(path)))
        self._update_title()

    def reload(self):
        if not self.path:
            return
        # Editors often save by rename, which drops the watch - re-arm it.
        if str(self.path) not in self.watcher.files() and self.path.exists():
            self.watcher.addPath(str(self.path))
        try:
            self.inject(self.read_rendered())
        except OSError:
            pass  # mid-save; the next change event will catch up

    def choose_file(self):
        start = self.settings.value("last_dir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Markdown file", start,
            "Markdown (*.md *.markdown *.mdown *.mkd *.mdx);;Text (*.txt);;All files (*)")
        if path:
            self.open_file(path)

    # ---- links

    def on_link(self, url):
        if url.isLocalFile():
            target = Path(url.toLocalFile())
            anchor = url.fragment(QUrl.ComponentFormattingOption.FullyDecoded) or None
            if self.path and target == self.path:
                if anchor:
                    self.page.runJavaScript(f"goto({json.dumps(anchor)})")
                return
            if target.suffix.lower() in MD_SUFFIXES and target.is_file():
                self.open_file(target, anchor)
                return
        QDesktopServices.openUrl(url)

    # ---- theme / zoom / find

    def set_theme(self, theme_id):
        if theme_id not in self.themes:
            return
        self.theme_id, self.theme = theme_id, self.themes[theme_id]
        self.settings.setValue("theme", theme_id)
        self.settings.setValue(f"theme_{self.theme['kind']}", theme_id)
        self.apply_theme()

    def apply_theme(self):
        # Swap the theme <style> in place - no reload, so the scroll position survives.
        self.page.setBackgroundColor(theme_bg(self.theme))
        self.page.runJavaScript(self._theme_js())
        self.apply_chrome()
        self._update_theme_action()
        self._fit_min_width()
        for a in self.theme_menu.actions():
            if a.isCheckable():
                a.setChecked(a.data() == self.theme_id)

    def _warn_box(self, text):
        box = QMessageBox(QMessageBox.Icon.Warning, "Markdown Reader", text, parent=self)
        box.setTextFormat(Qt.TextFormat.PlainText)  # paths are not markup
        box.exec()

    def _fit_min_width(self):
        # Never narrower than the toolbar: overflowing pushes the window buttons into ».
        self.setMinimumWidth(self.tb.sizeHint().width())

    def _theme_js(self):
        return f"setTheme({json.dumps(self.theme['kind'])}, {json.dumps(theme_css(self.theme))})"

    def toggle_theme(self):
        kind = "light" if self.theme["kind"] == "dark" else "dark"
        for theme_id in (self.settings.value(f"theme_{kind}"), kind):
            if theme_id in self.themes and self.themes[theme_id]["kind"] == kind:
                return self.set_theme(theme_id)
        others = sorted(i for i, t in self.themes.items() if t["kind"] == kind)
        if others:
            self.set_theme(others[0])

    def _watch_themes(self):
        old = self.theme_watcher.files() + self.theme_watcher.directories()
        if old:
            self.theme_watcher.removePaths(old)
        paths = [str(d) for d in (BUILTIN_THEMES, user_theme_dir()) if d.is_dir()]
        paths += [t["path"] for t in self.themes.values() if t["path"]]
        if paths:
            self.theme_watcher.addPaths(paths)

    def rescan_themes(self):
        themes, failed = load_themes()
        new = themes.get(self.theme_id)
        changed = False
        if self.theme["path"] in failed:
            themes[self.theme_id] = self.theme  # half-saved: keep the last good one, listed
        elif new is None:
            pass  # deleted: stays on screen (self.theme) but leaves the menu and the watch
        elif new != self.theme:
            self.theme, changed = new, True
        self.themes = themes
        self._watch_themes()
        self._build_theme_menu()
        if changed:
            self.apply_theme()

    def open_themes_folder(self):
        folder = user_theme_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self._warn_box(f"Could not create {folder}:\n{e}")
            return
        self._watch_themes()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def show_about(self):
        AboutDialog(self).exec()

    def toggle_outline(self, on):
        self.settings.setValue("outline", on)
        self.page.runJavaScript(f"setOutline({json.dumps(on)})", self._outline_feedback)

    def _outline_feedback(self, state):
        # Turned on but nothing appears: say why, briefly, instead of silently doing nothing.
        why = {"narrow": "Outline: the window is too narrow to show it beside the text",
               "few": "Outline: this document has fewer than two headings"}.get(state)
        if why and self.outline_action.isChecked():
            QToolTip.showText(self.view.mapToGlobal(QPoint(24, 24)), why, self.view, QRect(), 3000)

    def zoom(self, delta):
        z = 1.0 if delta is None else min(3.0, max(0.5, self.view.zoomFactor() + delta))
        self.view.setZoomFactor(z)
        self.settings.setValue("zoom", z)

    def start_find(self):
        self.find_box.setFocus()
        self.find_box.selectAll()

    def find_next(self, backward=False):
        flags = QWebEnginePage.FindFlag.FindBackward if backward else QWebEnginePage.FindFlag(0)
        self.view.findText(self.find_box.text(), flags)

    def eventFilter(self, obj, event):
        if obj is self.tb and self.frameless:
            if self._titlebar_event(event):
                return True
        if obj is self.find_box and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.find_box.clear()
                self.view.setFocus()
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
                    event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.find_next(backward=True)
                return True
        return super().eventFilter(obj, event)

    def _titlebar_event(self, event):
        """Empty title-bar space: drag moves the window, double-click maximises/restores."""
        t = event.type()
        if t == QEvent.Type.Resize or t == QEvent.Type.LayoutRequest:
            QTimer.singleShot(0, self._place_title)
            return False
        if t not in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove,
                     QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick):
            return False
        pos = event.position().toPoint()
        if t == QEvent.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
            self._drag_from = None
            self.toggle_maximized()
            return True
        if t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            if self._edges_at(self.tb.mapTo(self, pos)) != Qt.Edge(0):
                return False
            self._drag_from = pos  # move starts once the pointer travels, so double-click still works
            return True
        if t == QEvent.Type.MouseMove and self._drag_from is not None \
                and event.buttons() & Qt.MouseButton.LeftButton:
            if (pos - self._drag_from).manhattanLength() >= QApplication.startDragDistance():
                self._drag_from = None
                self.windowHandle().startSystemMove()
            return True
        if t == QEvent.Type.MouseButtonRelease:
            self._drag_from = None
        return False

    # ---- drag & drop, close

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.open_file(url.toLocalFile())
                break

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Markdown Reader")
    app.setDesktopFileName("mdreader")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(app_icon())
    win = Reader()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        win.open_file(args[0])
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
