# Memory Governance Basis — <YOUR WORKSPACE> (fill-in template)

**Status**: template — copy, fill the `<...>` slots, and commit to your
workspace's shared docs. Every agent with persistent memory in this
workspace follows this document.

## 1. Failure model

An agent's persistent memory is a point-in-time snapshot, not live state.
Status-bearing claims ("undeposited", "awaiting review", "tool X is
broken") become false the moment another session, another agent, or the
owner changes the world.

Record your own motivating incident here — a concrete near-miss makes the
discipline stick:

> <YYYY-MM-DD>: <agent> memory claimed "<stale claim>"; reality was
> "<actual state>" (canonical source: <where>). Acting on it would have
> caused <consequence>.

## 2. Principles

1. Verify status-bearing claims against primary sources before relying on
   them. Canonical order: machine-readable ledgers > filesystem reality >
   git history > public APIs > memory.
2. The session that changes durable state updates SHARED_STATE.md (and its
   own store) in the same session.
3. Write absolute dates ("as of 2026-01-15"), never relative ones.
4. Plant verification anchors: every status-bearing claim carries a
   `verify:` command / path / API.
5. Non-compensatory gating: a flagged claim is not usable until verified —
   however well-written it is. Flags are a review queue; nothing is
   auto-deleted.

## 3. Canon table (primary sources for THIS workspace)

| Subject | Canonical source |
|---|---|
| <releases / deposits> | <ledger file / registry API> |
| <CI / deploy state> | <command, e.g. `gh run list`> |
| <toolchain availability> | run it (`<tool> --version`) — never trust remembered failures |
| <...> | <...> |

## 4. Stores and responsibility boundaries

| Agent | Memory store | Who fixes it |
|---|---|---|
| <Claude Code> | <path> | that agent |
| <Codex> | <path> | that agent (product-managed files: route corrections via SHARED_STATE) |
| shared (live state) | SHARED_STATE.md | any agent — row overwrite |
| shared (narrative) | <handoff doc path> | any agent — dated appends |

Agents never edit each other's private stores.

## 5. On finding a stale fact

1. Overwrite the matching SHARED_STATE row (add one if missing) — this
   reaches every agent's next session automatically.
2. If it lives in your own store: fix in place, dated, with an anchor.
3. If it lives in another agent's store: SHARED_STATE row + a dated
   "stale-memory correction" note in the shared handoff doc.

## 6. Revision

Additions to the canon table are routine maintenance. Changes to the
principles (§2) require the owner's sign-off.
