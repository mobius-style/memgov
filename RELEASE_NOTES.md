# Release notes

## v0.2.0 (2026-08-21)

Both changes come from the first sustained live deployment, where the scan
reported the same 16 findings on every run and buried real drift.

- **Store kinds** (`index` | `log`): declare append-only session logs as
  `kind = "log"` in `memgov.toml`; their matches are reported as HISTORICAL
  and no longer count toward the drift total. Comparing a log against live
  state is a category error — 11 of the 16 permanent findings were this.
- **Adjudications**: `ADJUDICATIONS.jsonl` records investigated false
  positives with a required date and rationale; incomplete rows are ignored
  and warned about. Content-hash anchoring expires an adjudication the moment
  the underlying line changes. Suppressed findings stay listed in the
  CONFLICT_MAP with their reasons.
- **Matcher fix**: all-uppercase status markers (`HOLD`, `TBD`) now match
  case-sensitively on word boundaries. Calibrating v0.2.0 against a live
  workspace caught `HOLD` firing inside the English verb "holds" — the same
  class of false positive on every English-language store. Substring matching
  is kept for everything else (Japanese needs it).
- Scan result now carries `all_findings` and `suppressed` alongside the
  drift-only `findings`; the ledger records the suppression counts.
- 7 new tests (17 total), including: a log-store finding is historical, an
  adjudication without a rationale is not honoured, and editing an
  adjudicated line revives the finding.

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
