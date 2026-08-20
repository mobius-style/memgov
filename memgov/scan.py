"""Cross-store drift scan — the CONFLICT_MAP transplant.

SHARED_STATE.md holds committed-canonical rows (fact | current state |
verify anchor | key regex). A memory-store line is flagged as suspected
drift when it matches a resolved-type row's key regex AND carries a
stale/status marker AND does not itself contain a resolution word.

Non-compensatory rule: a flagged line is a review-queue item, never
auto-deleted; only verification against the row's anchor clears it.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .config import Config

_CELL_SPLIT = re.compile(r"(?<!\\)\|")  # respect escaped pipes in keys


def _alternation(words: list[str]) -> re.Pattern:
    """Compile a marker list. All-uppercase alphabetic markers (HOLD, TBD…) are
    status codes, not words: matched case-sensitively and on word boundaries,
    or 'HOLD' fires inside 'holds', 'threshold' and 'placeholder' on every
    English-language store (found by calibration against a live workspace).
    Everything else keeps the original case-insensitive substring behaviour,
    which is what non-segmented scripts like Japanese need."""
    parts = []
    for w in words:
        esc = re.escape(w)
        if w.isascii() and w.isalpha() and w.isupper():
            parts.append(rf"\b{esc}\b")
        else:
            parts.append(rf"(?i:{esc})")
    return re.compile("|".join(parts))


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


# Adjudicated false positives. Every row MUST carry an adjudication date and a
# rationale — the point of the allowlist is to preserve *why* something was
# silenced, not merely to silence it. A suppression whose reason is lost is
# worse than a false positive, because nobody can audit it later; rows missing
# a required field are ignored and warned about, never honoured.
ADJUDICATION_REQUIRED = ("store", "text_sha256", "entity", "adjudicated", "rationale")


def line_key(store: str, entity: str, text: str) -> str:
    """Stable anchor for one finding: store + entity + whitespace-normalized
    line, hashed. Anchoring on content rather than a line number means editing
    the adjudicated line expires its adjudication automatically."""
    norm = " ".join(text.split())
    return hashlib.sha256(f"{store}|{entity}|{norm}".encode()).hexdigest()


def load_adjudications(cfg: Config, warnings: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    path = cfg.adjudications_path
    if not path.is_file():
        return out
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            warnings.append(f"{path.name}:{n} ignored — not JSON")
            continue
        missing = [k for k in ADJUDICATION_REQUIRED if not row.get(k)]
        if missing:
            warnings.append(f"{path.name}:{n} ignored — missing {missing}")
            continue
        out[row["text_sha256"]] = row
    return out


def scan(cfg: Config) -> dict:
    rows, warnings = parse_shared_state(cfg)
    stale_re = _alternation(cfg.stale_markers)
    resolution_re = _alternation(cfg.resolution_words)
    adjudicated = load_adjudications(cfg, warnings)
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
                        key = line_key(store, row["entity"], line)
                        adj = adjudicated.get(key)
                        if adj:
                            klass = "adjudicated"
                        elif cfg.kind_of(store) == "log":
                            klass = "historical"
                        else:
                            klass = "drift"
                        findings.append({
                            "store": store, "file": f.name, "line": i,
                            "entity": row["entity"],
                            "shared_state": row["state"],
                            "verify": row["verify"],
                            "text": line.strip()[:200],
                            "class": klass, "key": key,
                            "adjudication": ({"adjudicated": adj["adjudicated"],
                                              "rationale": adj["rationale"]}
                                             if adj else None),
                        })
                        break
    drift = [f for f in findings if f["class"] == "drift"]
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files_scanned": files_scanned,
        "rows_watched": len(rows),
        "warnings": warnings,
        "findings": drift,
        "all_findings": findings,
        "suppressed": {
            "historical": sum(1 for f in findings if f["class"] == "historical"),
            "adjudicated": sum(1 for f in findings if f["class"] == "adjudicated"),
        },
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

    others = [f for f in result.get("all_findings", []) if f["class"] != "drift"]
    if others:
        sup = result.get("suppressed", {})
        lines += [
            "", "---", "",
            "## Suppressed (not drift)",
            "",
            f"`historical` {sup.get('historical', 0)} · "
            f"`adjudicated` {sup.get('adjudicated', 0)}. Listed in full so the",
            "suppression stays auditable — a silenced finding whose reason is",
            "lost is worse than a false positive.",
            "",
        ]
        for fd in others:
            lines.append(f"- **{fd['class']}** `{fd['store']}` "
                         f"`{fd['file']}:{fd['line']}` ({fd['entity']})")
            if fd.get("adjudication"):
                a = fd["adjudication"]
                lines.append(f"  - adjudicated {a['adjudicated']}: {a['rationale']}")
            else:
                lines.append("  - append-only log store; a stale statement there "
                             "is correct as history (kind = log)")
    if result["warnings"]:
        lines += ["", "## Warnings", ""]
        lines += [f"- {w}" for w in result["warnings"]]
    cfg.conflict_map_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    entry = {k: v for k, v in result.items()
             if k not in ("findings", "all_findings")}
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
