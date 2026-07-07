---
name: memory-restore
description: Reconcile status-bearing claims in persistent memory (pending / awaiting / TBD / "tool X is broken") against primary sources before relying on them. Use when a SessionStart hook injects "memory-restore due" or "suspected drift(s)", or whenever a memory claim contradicts observed reality.
---

# memory-restore — reconcile memory against ground truth

## Failure model

Persistent memory is a point-in-time snapshot, not live state. Status-bearing
claims ("undeposited", "awaiting review", "tool X is broken") go stale the
moment another session, another agent, or the owner changes the world.
Acting on a stale claim causes double-work or damage.

## Principles

1. **Verify status-bearing claims against primary sources before relying on
   them.** Canonical order: machine-readable ledgers > filesystem reality
   (existence, mtime) > git history > public APIs > memory.
2. **Fix in place with an absolute date.** Memory mirrors current facts; keep
   history only where it carries context. Update index lines too.
3. **Plant a verification anchor.** After verifying, append a `verify:` line
   (command / path / API) next to the claim so the next pass is mechanical.
4. **The session that changes state updates memory in the same session.**
   This skill is the safety net, not a license to write stale notes.

## Procedure

1. Run `memgov fresh` and `memgov scan` (or read the SessionStart injection).
2. For each flagged item, execute its verify anchor — or derive one from your
   workspace's canon table in SHARED_STATE.md / your basis document.
3. Correct stale claims in the owning store. Never edit another agent's
   private store: update the SHARED_STATE row instead (the row overwrite IS
   the cross-agent handoff) and note the correction in your handoff doc.
4. When a store is reconciled: `memgov mark-restored <store>`.
5. Report: claims checked / corrected (before → after) / items needing the
   owner's judgment.
