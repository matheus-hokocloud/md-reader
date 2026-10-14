# Workflow

- Nothing non-trivial is done until `review-agent` has reviewed it and its findings are
  fixed or explicitly accepted by the user. Run the review in a fresh agent, never in the
  one that made the change.
- Changes touching auth, user input, sensitive data, dependencies, secrets or network
  exposure also get a `security-agent` review.
- Route findings back to the owning agent; reviewers report, owners fix.
