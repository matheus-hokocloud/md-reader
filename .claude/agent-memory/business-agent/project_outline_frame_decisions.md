---
name: project-outline-frame-decisions
description: 2026-10-14 outline panel (Ctrl+Shift+O), frameless themed window frame with native fallback, About dialog revision by Virgilio
metadata:
  type: project
---

2026-10-14: added a left-margin outline (h1–h3, Ctrl+Shift+O, auto-hide when narrow, hidden under 2 headings) and a frameless themed title bar (startSystemMove/Resize, native-decoration fallback). Virgilio revised About: centred, version at bottom, no Mascot/tech lines, GitHub icon instead of URL text.

**Why:** his own requests; both are navigation/appearance only, so read-only holds. The About revision supersedes the earlier "About shows tech stack" rule.

**How to apply:** outline must never cover text; chrome colours assumed derived from existing theme colors (no new keys) until he says otherwise. Watch the "simple" rule: custom frame adds complexity, which is why native fallback is required. Related: [[project-themes-sparrow-decisions]], [[project-author-identity]] (which repo the GitHub icon opens is still open).
