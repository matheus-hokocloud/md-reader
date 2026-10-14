---
name: commit
description: Create a git commit for the current changes using Conventional Commits. Use when the user asks to commit.
disable-model-invocation: true
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git log:*)
---

# Commit

1. **Inspect.** Run `git status` and `git diff`. If the changes hold more than one logical
   change, propose splitting them into separate commits.
2. **Check readiness.** Non-trivial changes must have passed review (see
   `.claude/rules/workflow.md`). If not, say so and stop unless the user says to go ahead.
3. **Stage** files by name; never `git add -A` blindly. Read `git diff --staged` and make
   sure no secrets, `.env` files, credentials or local settings are included.
4. **Write the message** in [Conventional Commits](https://www.conventionalcommits.org/)
   format and commit:

   ```
   <type>(<optional scope>): <subject>

   <body: what changed and why, wrapped at 72>
   ```

   - **Types:** `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`.
     Breaking changes add `!` after the type and a `BREAKING CHANGE:` footer.
   - **Subject:** imperative, lowercase, no trailing period, at most 72 characters.
   - **Body:** explain why, not how; skip it only when the subject says everything.
   - Match the style of recent messages in `git log`.
5. **Report** the commit hash and subject. Do not push unless asked.
