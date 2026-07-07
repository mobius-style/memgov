# Release notes

## v0.1.0 (2026-07-07)

First public slice. Extracted and generalized from a live two-agent
(Claude Code + GPT Codex) workspace where the mechanism runs at every
session start.

- `memgov init | scan | fresh | hook-context | mark-restored`
- SHARED_STATE.md committed-canonical table with key-regex matching
  (escaped-pipe safe)
- Cross-store drift scan with CONFLICT_MAP + append-only measurement
  ledger (LEDGER.jsonl)
- Freshness check with `.last_restored` suppression markers
- Single `hook-context` JSON output consumed unchanged by both Claude Code
  and Codex SessionStart hooks
- Adapters: Claude Code settings snippet + memory-restore skill; Codex
  hooks snippet + AGENTS.md section
- 10 tests; stdlib-only runtime (Python 3.11+)

Known limits (deliberate): regex-level detection (no embeddings/LLM);
`*.md` stores only; per-store granularity for `mark-restored`.
