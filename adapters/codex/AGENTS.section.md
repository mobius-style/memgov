# Memory Restore Discipline (paste into ~/.codex/AGENTS.md or repo AGENTS.md)

## Memory Restore Discipline

- **Memories are point-in-time snapshots, not live state.** Before relying on
  any status-bearing memory (pending / awaiting / HOLD / TBD / "tool X is
  broken"), verify it against primary sources: ledgers > filesystem reality >
  git history > public APIs > memory.
- **Cross-agent live state lives in SHARED_STATE.md** (see memgov.toml for
  its location) — a small current-state table auto-injected at SessionStart
  for every agent via `memgov hook-context`. When your session changes
  durable state (publish, deploy, repair, delete), overwrite the matching row
  in the same session, with an absolute date and a verification anchor.
  Narrative history goes to your handoff doc; the row overwrite IS the
  handoff.
- **Never edit another agent's private memory store.** If you find a stale
  fact there, fix the SHARED_STATE row and leave a dated correction note in
  the shared handoff doc.
- When the SessionStart context shows "memory-restore due" or "suspected
  drift(s)", reconcile before relying on the flagged files, then run
  `memgov mark-restored <store>`.
