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
- Icons: `assets/icons/mdreader-{16,32,48,64,128,256}.png`, if present, are copied to
  `~/.local/share/icons/hicolor/<N>x<N>/apps/mdreader.png` and the entry gets `Icon=mdreader`
  (otherwise `Icon=text-markdown`). Not yet re-run with icons — ask before running.
- `xdg-mime` prints `qtpaths: comando não encontrado` twice — harmless, the default is still set.
- If Dolphin still offers Kate, run `kbuildsycoca6` to refresh KDE's cache.

## Rollback

```bash
rm ~/.local/bin/mdreader ~/.local/share/applications/mdreader.desktop
rm -f ~/.local/share/icons/hicolor/*/apps/mdreader.png
xdg-mime default org.kde.kate.desktop text/markdown text/x-markdown
```

## Config and secrets

No secrets. User state lives in `~/.config/mdreader/mdreader.conf` (QSettings): `theme`
(active theme id), `theme_light` / `theme_dark` (last-used theme per kind, for Ctrl+T),
`zoom`, `geometry`, `last_dir`, `outline` (outline shown, default `true`; Ctrl+Shift+O),
`native_frame` (`true` = KDE window decorations instead of the reader's own title bar; default
`false`; read at startup, so a change applies on the next launch). Deleting it resets to defaults.
If the custom title bar ever misbehaves, `native_frame=true` under `[General]` restores the KDE frame.

Themes: built-ins in the repo's `themes/*.json`; user themes in
`~/.config/mdreader/themes/*.json` (honours `$XDG_CONFIG_HOME`), which override built-ins with
the same id. Both are watched and re-applied live; a user folder created outside the app is
picked up the next time the Theme menu is opened. `$XDG_CONFIG_HOME` is ignored if relative. Bad theme files are skipped with a
`mdreader: theme …` warning on stderr.

## Observability

None needed: a desktop app run on demand. Errors go to stderr; launch from a terminal
(`python3 mdreader.py FILE`) to see them. Qt prints harmless D-Bus warnings when run offscreen.
