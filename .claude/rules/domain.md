# Domain context

`business-agent` feeds the other agents what they need to know about the domain.

- On new or non-trivial work, consult `business-agent` first for requirements and a
  briefing, then pass that briefing to the agents doing the work.
- When an agent reports missing domain knowledge, route the question to `business-agent`
  (or to the user, if it is an open question) before resuming that agent.
- Keep `docs/domain.md` current: new rules and decisions go there, not only into a task.
