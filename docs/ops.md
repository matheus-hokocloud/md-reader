# Operations

Owned by `ops-agent`. How the project is built, deployed and run.

## Environments

Only one: Virgilio's desktop (CachyOS, KDE Plasma 6, Wayland). Runtime is the system Python
3.14 with Arch packages `pyside6`, `qt6-webengine`, `python-markdown-it-py`,
`python-pygments`. No virtualenv, no pip, no build step.

## Build and deploy

`./install.sh` installs for the current user (run 2026-10-13):

- `~/.local/bin/mdreader` → symlink to `mdreader.py` (so edits to the repo take effect
  immediately; moving the repo breaks the link — re-run `install.sh`).
- `~/.local/share/applications/mdreader.desktop` ("Markdown Reader", `Exec=… %f`,
  `MimeType=text/markdown;text/x-markdown;`).
- `xdg-mime default mdreader.desktop text/markdown text/x-markdown`, written to
  `~/.config/mimeapps.list`. The previous default was `org.kde.kate.desktop`.
- `xdg-mime` prints `qtpaths: comando não encontrado` twice — harmless, the default is still set.
- If Dolphin still offers Kate, run `kbuildsycoca6` to refresh KDE's cache.

## Rollback

```bash
rm ~/.local/bin/mdreader ~/.local/share/applications/mdreader.desktop
xdg-mime default org.kde.kate.desktop text/markdown text/x-markdown
```

## Config and secrets

No secrets. User state lives in `~/.config/mdreader/mdreader.conf` (QSettings): `theme`,
`zoom`, `geometry`, `last_dir`. Deleting it resets to defaults.

## Observability

None needed: a desktop app run on demand. Errors go to stderr; launch from a terminal
(`python3 mdreader.py FILE`) to see them. Qt prints harmless D-Bus warnings when run offscreen.
