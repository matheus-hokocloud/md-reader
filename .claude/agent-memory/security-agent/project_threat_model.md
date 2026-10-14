---
name: threat-model-summary
description: md-reader threat model pointers and past security findings (untrusted Markdown, theme JSON files) with their status
metadata:
  type: project
---

Full threat model lives in docs/security.md (owned by security-agent); this is the history.

- **Untrusted Markdown with JS + file:// access** — open since 2026-10-13, not yet assessed or mitigated. Highest-value item still outstanding.
  **Why:** reader is the default `text/markdown` handler, so hostile .md from downloads/repos lands here.
  **How to apply:** prioritise this when asked for next security work.
- **Theme JSON review (2026-10-14, feat/themes-sparrow)** — colour/key/kind/pygments/name handling found sound (injection attempts tested and rejected). Findings: FIFO in theme dir hangs app (stat-size cap + unbounded read_text); symlink to /dev/zero -> MemoryError (uncaught) crash at startup; validator accepts syntactically bogus `rgb(....,..,..)` (robustness only). All Low — trust boundary is the user's own config dir. All three fixed by code-agent and verified by review-agent the same day (`_read_small`, strict `_NUM`).
- **Title-bar tooltip (2026-10-14)** — `title_label.setToolTip(str(self.path))` is auto-detected as rich text, so crafted file names render markup in the tooltip. Low, reported, not yet fixed.
  **How to apply:** re-check on the next review of the frameless title bar.
