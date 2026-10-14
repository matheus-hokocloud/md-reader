---
name: project-themes-sparrow-decisions
description: 2026-10-14 decisions on JSON themes, Ctrl+T semantics, Sparrow mascot/icon, and why they don't break read-only
metadata:
  type: project
---

2026-10-14: themes became JSON files (built-ins in repo `themes/`, user overrides in ~/.config/mdreader/themes); Ctrl+T now = last-used theme of the other kind; Sparrow mascot, B/W pixel icon, About dialog.

**Why:** Virgilio asked for custom themes ("json file as editor") and a mascot. Read-only rule holds because themes are edited in an external editor — no in-app editor. Assumed About art is colour (only icon was specified B/W).

**How to apply:** Reject any in-app theme editor or document-writing feature as drifting from read-only unless he asks. Old settings value `light`/`dark` must remain valid theme ids. Open: licence, version, author handle (see [[project-author-identity]]).
