#!/usr/bin/env python3
"""mdreader - a small, read-only Markdown viewer with light/dark themes.

Usage: mdreader [FILE.md]

Keys: Ctrl+O open · Ctrl+T toggle theme · Ctrl+F find · Ctrl+R reload
      Ctrl+= / Ctrl+- / Ctrl+0 zoom · Ctrl+Q quit
The open file is watched and re-rendered in place when it changes on disk.
"""
import json
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound
from PySide6.QtCore import QFileSystemWatcher, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QApplication, QFileDialog, QLineEdit, QMainWindow, QMessageBox,
                               QSizePolicy, QToolBar, QWidget)

MD_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd", ".mdx", ".txt"}
BG = {"light": "#fbfbfa", "dark": "#16171a"}

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


def _pygments_css():
    light = HtmlFormatter(style="default").get_style_defs("html.light pre")
    dark = HtmlFormatter(style="github-dark").get_style_defs("html.dark pre")
    return light + "\n" + dark


CSS = """
:root { color-scheme: light; }
html.light {
  --bg: #fbfbfa; --fg: #1f2328; --muted: #5d6570; --border: #d9dde3;
  --soft: #f1f3f5; --code-bg: #f3f4f6; --link: #0b62d6; --accent: #0b62d6;
  --stripe: #f6f7f9; --mark: #fff3b0;
}
html.dark {
  color-scheme: dark;
  --bg: #16171a; --fg: #d9dce1; --muted: #8c939e; --border: #30343b;
  --soft: #1e2025; --code-bg: #1d1f24; --link: #6aa8ff; --accent: #6aa8ff;
  --stripe: #1b1d21; --mark: #5c4d12;
}
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
.alert-note { --alert: #4493f8; }
.alert-tip { --alert: #2da44e; }
.alert-important { --alert: #8957e5; }
.alert-warning { --alert: #c48a00; }
.alert-caution { --alert: #d1242f; }

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
"""

PAGE = """<!doctype html>
<html class="{theme}"><head><meta charset="utf-8">
<style>{pygments}</style><style>{css}</style>
<script>
function render(html) {{ document.getElementById('content').innerHTML = html; }}
function setTheme(t) {{ document.documentElement.className = t; }}
function goto(id) {{ const el = document.getElementById(id); if (el) el.scrollIntoView(); }}
</script></head>
<body><article id="content">{body}</article></body></html>"""

EMPTY = ('<div class="empty"><p><b>No file open</b></p>'
         "<p>Press Ctrl+O, or drop a Markdown file on this window.</p></div>")

# --------------------------------------------------------------------------- window


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
    def __init__(self):
        super().__init__()
        self.settings = QSettings("mdreader", "mdreader")
        self.path = None
        self.pending_anchor = None

        theme = self.settings.value("theme")
        if theme not in BG:
            dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
            theme = "dark" if dark else "light"
        self.theme = theme

        self.view = QWebEngineView(self)
        self.view.setAcceptDrops(False)
        self.page = Page(self.on_link, self.view)
        self.page.setBackgroundColor(QColor(BG[self.theme]))
        self.view.setPage(self.page)
        self.view.loadFinished.connect(self.on_loaded)
        self.view.setZoomFactor(float(self.settings.value("zoom", 1.0)))
        self.setCentralWidget(self.view)
        self.setAcceptDrops(True)

        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(lambda _: self.reload_timer.start())
        self.reload_timer = QTimer(self, singleShot=True, interval=150)
        self.reload_timer.timeout.connect(self.reload)

        self._build_toolbar()
        self.css_bundle = (_pygments_css(), CSS)
        self.load_page(EMPTY, QUrl())

        geom = self.settings.value("geometry")
        if geom is not None:
            self.restoreGeometry(geom)
        else:
            self.resize(980, 900)
        self._update_title()

    # ---- UI

    def _build_toolbar(self):
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
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
        self._update_theme_action()

        self.find_box = QLineEdit(self)
        self.find_box.setPlaceholderText("Find (Ctrl+F)")
        self.find_box.setClearButtonEnabled(True)
        self.find_box.setMaximumWidth(260)
        self.find_box.textChanged.connect(lambda t: self.view.findText(t))
        self.find_box.returnPressed.connect(self.find_next)
        self.find_box.installEventFilter(self)
        stretch = QWidget(self)
        stretch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(stretch)
        tb.addWidget(self.find_box)

    def _update_theme_action(self):
        if self.theme == "dark":
            self.theme_action.setText("Light mode")
            self.theme_action.setIcon(QIcon.fromTheme("weather-clear"))
        else:
            self.theme_action.setText("Dark mode")
            self.theme_action.setIcon(QIcon.fromTheme("weather-clear-night"))
        self.theme_action.setToolTip(f"{self.theme_action.text()} (Ctrl+T)")

    def _update_title(self):
        name = self.path.name if self.path else "Markdown Reader"
        self.setWindowTitle(f"{name} — Markdown Reader" if self.path else name)

    # ---- page loading

    def load_page(self, body, base_url):
        pyg, css = self.css_bundle
        self._pending_body = body
        # Content is injected after load: setHtml caps at 2 MB, runJavaScript doesn't.
        html = PAGE.format(theme=self.theme, pygments=pyg, css=css, body="")
        self.view.setHtml(html, base_url)

    def on_loaded(self, ok):
        if ok and self._pending_body is not None:
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
            QMessageBox.warning(self, "Markdown Reader", f"Could not open {path}:\n{e}")
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

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings.setValue("theme", self.theme)
        self.page.setBackgroundColor(QColor(BG[self.theme]))
        self.page.runJavaScript(f"setTheme({json.dumps(self.theme)})")
        self._update_theme_action()

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
    win = Reader()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        win.open_file(args[0])
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
