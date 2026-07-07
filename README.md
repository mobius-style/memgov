# memgov — cross-agent memory governance

Gate what an AI agent's **persistent memory** may assert before the agent
relies on it. Local-first, deterministic, stdlib-only (Python 3.11+).

> Memory is a point-in-time snapshot, not live state.

`memgov` transplants the [RCGov](https://github.com/mobius-style/rcgov)
axiom — `InjectContext_t ⇒ ContextReady_t`, *govern what a model reads
before it answers* — onto the memory layer of coding agents (Claude Code,
GPT Codex, and anything else whose memory is Markdown on disk).

## The failure it prevents

Two agents share a workspace. Agent A's memory says a paper is
"not yet deposited". In reality it was published yesterday — by a session
that didn't update A's memory. A, trusting its memory, deposits it again.

Multiply that by every status-bearing claim agents write down: "awaiting
review", "CI is broken", "tool X can't start". Each goes stale silently the
moment another session, another agent, or the human changes the world.

## What memgov does

1. **SHARED_STATE.md** — a small, human-readable table of *committed
   canonical* live state: fact, current state (dated), verification anchor,
   and a key regex. The session that changes durable state overwrites the
   matching row — **the row overwrite is the cross-agent handoff.**
2. **`memgov scan`** — cross-store drift detection (the CONFLICT_MAP):
   flags memory lines that match a resolved row's key while still carrying a
   stale/status marker. Non-compensatory: flagged lines are a review queue,
   never auto-deleted; only verification clears them. Every pass appends to
   a measurement ledger (`LEDGER.jsonl`) — clean passes are evidence too.
3. **`memgov fresh`** — freshness check: status-bearing memory files
   untouched for N days get flagged before an agent relies on them.
4. **`memgov hook-context`** — one command that emits the SessionStart
   context block (SHARED_STATE + freshness + drift summary) in the
   `hookSpecificOutput` JSON schema **accepted by both Claude Code and
   Codex hooks unchanged**.

## Quickstart

```bash
pip install .            # or: run in-place with python3 -m memgov
cd /path/to/your/workspace
python3 -m memgov init   # scaffolds memgov.toml + SHARED_STATE.md
$EDITOR memgov.toml      # point [stores] at your agents' memory dirs
python3 -m memgov scan --summary
python3 -m memgov hook-context   # what your agents will see at SessionStart
```

Then wire the SessionStart hooks:

- **Claude Code**: merge `adapters/claude-code/settings.snippet.json` into
  `~/.claude/settings.json`; optionally install
  `adapters/claude-code/skills/memory-restore/` as a skill.
- **Codex**: merge `adapters/codex/hooks.snippet.json` into
  `<repo>/.codex/hooks.json`; paste `adapters/codex/AGENTS.section.md` into
  your `AGENTS.md`.

## Discipline (the part software can't do for you)

- Status-bearing memories get an **absolute date** and a **verify anchor**
  (a command / path / API that yields ground truth).
- The session that changes state updates SHARED_STATE **in the same
  session**. The tooling is the safety net, not a license to write stale
  notes.
- Agents never edit each other's private stores; corrections flow through
  SHARED_STATE rows. See `docs/MEMORY_GOVERNANCE_BASIS.template.md` for the
  fill-in governance document.

## Design lineage

`memgov` is the memory-domain sibling of
[RCGov](https://github.com/mobius-style/rcgov) (context governor) and a
cousin of [mmv-secretary](https://github.com/mobius-style/mmv-secretary)
(session continuity clerk). Concept mapping: SHARED_STATE rows ≈ RCGov's
Authority Commitment Gate; `scan` output ≈ CONFLICT_MAP + Non-Injection
Report; the review-queue rule ≈ non-compensatory gating.

## What it deliberately is NOT

No embeddings, no LLM calls, no background daemon, no writes to your memory
stores (except the opt-in `.last_restored` marker). Detection is regex over
Markdown — conservative, auditable, tunable in `memgov.toml`.

## Development

```bash
python3 -m pytest tests/ -q   # 10 tests, stdlib + pytest only
```

## License

Code: AGPL-3.0-or-later. Documentation under `docs/`: CC BY-NC-SA 4.0
(see `docs/LICENSE-DOCS.md`).
