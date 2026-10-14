# Git

Always-on guardrails. To make a commit, use the `/commit` skill.

- Commit or push only when the user asks.
- Never commit secrets, `.env` files, credentials, or local settings.
- Work on a branch; don't commit straight to `main` once it has history.
- Never force-push, rewrite or amend pushed commits, and never skip hooks (`--no-verify`),
  unless the user explicitly asks.
