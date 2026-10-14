# Markdown Reader

A small, read-only Markdown viewer for Virgilio's KDE desktop: open a `.md` file, read it
rendered, in a JSON theme of choice. Mascot: the Sparrow. Python + PySide6/QtWebEngine, `markdown-it-py` and Pygments —
all from Arch packages, no pip. It is the default app for `text/markdown` on this machine.

## Commands

- Run: `python3 mdreader.py [FILE.md]` (or `mdreader FILE.md` once installed)
- Screenshot themes: `python3 tools/screenshot.py [--theme ID|all] [--width N] [FILE.md] [OUT_DIR]` → `<ID>.png`
  (default `light`, `dark` at 900 px; the outline needs `--width 1080`+)
- Render to HTML only: `python3 -c "import mdreader; print(mdreader.render_markdown(open('sample.md').read()))"`
- Install / set as default app: `./install.sh` — changes system state, ask first (run 2026-10-13, not re-run since); rollback in `docs/ops.md`

## Code map

- `mdreader.py` — the whole app: `render_markdown` (markdown-it + Pygments, heading ids,
  task lists, alerts, front matter), theme loading/validation (`load_themes`, `theme_css`,
  `chrome_css`), `CSS`/`PAGE`/`OUTLINE_JS` templates, `AboutDialog`, `Page` (link
  interception), `Reader` (frameless themed title bar, theme menu, outline, find, zoom,
  live reload of file and themes, drag & drop)
- `themes/*.json` — built-in themes (`light`, `dark`, `solarized-light`, `solarized-dark`,
  `monokai`); user themes in `~/.config/mdreader/themes/` override by id
- `assets/` — `sparrow.png` (About art), `icons/mdreader[-N].png` (app icon), `github.svg`;
  sources and regeneration in `assets/README.md`
- `tools/screenshot.py` — offscreen render of a file in one or more themes
- `install.sh` — user launcher, `.desktop` entry, default-app association
- `sample.md` — test fixture covering the supported Markdown features

## Domain

What this software is for and its rules live in `docs/domain.md`. `business-agent`
maintains it and briefs the other agents (see `.claude/rules/domain.md`). Read it before
building anything non-trivial.

## Claude Code layout

```
.claude/
├── settings.json   shared settings (permissions, hooks, env) — committed
├── rules/          *.md, auto-loaded as instructions; scope with `paths:` frontmatter
├── agents/         *.md subagents (frontmatter: name, description, tools, model, memory, hooks)
├── agent-memory/   per-agent persistent memory, written by agents with `memory: project`
├── hooks/          scripts run by hooks (e.g. review-agent's write guard)
└── skills/         <name>/SKILL.md, invoked on demand or as /<name>
```

### Agents

| Agent | Owns |
|---|---|
| `business-agent` | The domain: purpose, users, rules, requirements — maintains `docs/domain.md` |
| `code-agent` | Features, bug fixes, refactors |
| `review-agent` | Independent read-only review of every non-trivial change |
| `test-agent` | Unit, integration and end-to-end tests |
| `interface-agent` | Public contracts: APIs, CLI flags, events, module boundaries |
| `ux-agent` | UI design, components, flows, accessibility |
| `art-agent` | Asset creation and pipeline, visual identity, art-direction review |
| `ops-agent` | CI/CD, releases, containers, config and secrets, observability — `docs/ops.md` |
| `security-agent` | Threat model, security review, secret/dependency scans, hardening — `docs/security.md` |

Each agent has `memory: project`, so its notes persist in `.claude/agent-memory/<agent>/`.

- Keep this file short and project-specific; put standing rules in `.claude/rules/`.
- New skill: `.claude/skills/<name>/SKILL.md` with `name` and `description` frontmatter.
- Commits: `/commit` skill (`.claude/skills/commit/`); git guardrails in `.claude/rules/git.md`.
- Personal overrides go in `.claude/settings.local.json` and `CLAUDE.local.md` (gitignored).
