# SHARED_STATE — cross-agent live state

Rules:
- **Current state only.** Narrative history belongs in your handoff docs.
- The session (any agent) that changes durable state **overwrites the
  matching row immediately** — the row overwrite IS the handoff.
- Every row carries an absolute date and a verification anchor. No secrets.
- Both agents' SessionStart hooks inject this file (`memgov hook-context`).
- The **key** column is the regex `memgov scan` uses to match this fact in
  memory stores. Escape literal pipes inside a key as `\|`.

| Fact | Current state (date) | Verify | Key (regex) |
|---|---|---|---|
| Example: release v1.2 | **published** (2026-01-15, tag v1.2.0) | `git tag --list v1.2*` | `v1\.2\|release` |
| Example: CI pipeline | operational (2026-01-10, flake fixed) | `gh run list -L 3` | `CI\|pipeline\|flaky` |
