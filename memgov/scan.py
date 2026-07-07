"""Cross-store drift scan — the CONFLICT_MAP transplant.

SHARED_STATE.md holds committed-canonical rows (fact | current state |
verify anchor | key regex). A memory-store line is flagged as suspected
drift when it matches a resolved-type row's key regex AND carries a
stale/status marker AND does not itself contain a resolution word.

Non-compensatory rule: a flagged line is a review-queue item, never
auto-deleted; only verification against the row's anchor clears it.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .config import Config

_CELL_SPLIT = re.compile(r"(?<!\\)\|")  # respect escaped pipes in keys


def _alternation(words: list[str]) -> re.Pattern:
    return re.compile("|".join(re.escape(w) for w in words), re.IGNORECASE)


def parse_shared_state(cfg: Config) -> tuple[list[dict], list[str]]:
    """Return (resolved-type rows with compiled key regex, warnings)."""
    rows: list[dict] = []
    warnings: list[str] = []
    if not cfg.shared_state.exists():
        return rows, [f"shared_state not found: {cfg.shared_state}"]
    resolved_re = _alternation(cfg.resolved_markers)
    for line in cfg.shared_state.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        cells = [c.strip() for c in _CELL_SPLIT.split(stripped.strip("|"))]
        if len(cells) < 4 or not cells[3] or not cells[0]:
            continue
        if cells[3].lower().startswith(("key", "キー")):
            continue  # header row
        if not resolved_re.search(cells[1]):
            continue  # genuinely-pending facts are not drift references
        key = cells[3].strip("`").replace("\\|", "|")
        try:
            rows.append({
                "entity": cells[0],
                "state": cells[1],
                "verify": cells[2],
                "key_re": re.compile(key, re.IGNORECASE),
            })
        except re.error as exc:
            warnings.append(f"bad key regex for row {cells[0]!r}: {key} ({exc})")
    return rows, warnings


def scan(cfg: Config) -> dict:
    rows, warnings = parse_shared_state(cfg)
    stale_re = _alternation(cfg.stale_markers)
    resolution_re = _alternation(cfg.resolution_words)
    findings: list[dict] = []
    files_scanned = 0
    for store, root in sorted(cfg.stores.items()):
        root = root.expanduser()
        if not root.is_dir():
            warnings.append(f"store missing: {store} -> {root}")
            continue
        for f in sorted(root.glob("*.md")):
            files_scanned += 1
            try:
                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError as exc:
                warnings.append(f"unreadable: {f} ({exc})")
                continue
            for i, line in enumerate(lines, 1):
                if not stale_re.search(line) or resolution_re.search(line):
                    continue
                for row in rows:
                    if row["key_re"].search(line):
                        findings.append({
                            "store": store, "file": f.name, "line": i,
                            "entity": row["entity"],
                            "shared_state": row["state"],
                            "verify": row["verify"],
                            "text": line.strip()[:200],
                        })
                        break
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files_scanned": files_scanned,
        "rows_watched": len(rows),
        "warnings": warnings,
        "findings": findings,
    }


def write_outputs(cfg: Config, result: dict) -> None:
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# CONFLICT_MAP (latest) — cross-store memory drift",
        "",
        f"Scanned: {result['ts']} — {result['files_scanned']} files, "
        f"{result['rows_watched']} watched rows, "
        f"**{len(result['findings'])} suspected drift(s)**.",
        "",
        "Non-compensatory rule: verify each flagged line against the row's",
        "verify anchor before relying on it. Fix the owning store (or",
        "SHARED_STATE if IT is stale), then re-run.",
        "",
    ]
    for fd in result["findings"]:
        lines += [
            f"## {fd['entity']}",
            f"- store: `{fd['store']}` / `{fd['file']}:{fd['line']}`",
            f"- memory says: {fd['text']}",
            f"- SHARED_STATE says: {fd['shared_state']}",
            f"- verify via: {fd['verify']}",
            "",
        ]
    if not result["findings"]:
        lines.append("No suspected drift. (A clean pass is also evidence.)")
    if result["warnings"]:
        lines += ["", "## Warnings", ""]
        lines += [f"- {w}" for w in result["warnings"]]
    cfg.conflict_map_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    entry = {k: v for k, v in result.items() if k != "findings"}
    entry["findings"] = len(result["findings"])
    with open(cfg.ledger_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def summary_line(cfg: Config, result: dict) -> str:
    n = len(result["findings"])
    if not n:
        return ""
    entities = ", ".join(sorted({f["entity"] for f in result["findings"]}))
    return (f"memory-governance: {n} suspected drift(s) [{entities}] — "
            f"see {cfg.conflict_map_path}")
