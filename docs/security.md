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

## Accepted risks

None yet.
