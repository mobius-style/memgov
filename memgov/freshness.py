"""Freshness check — flag status-bearing memory files gone stale.

A memory file that carries stale/status markers and has not been touched
for `stale_days` is a candidate for reconciliation before reliance.
A `.last_restored` marker (unix epoch) in a store dir suppresses
re-notification for `suppress_days` after a reconciliation pass.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from .config import Config


def check(cfg: Config, now: float | None = None) -> list[dict]:
    now = time.time() if now is None else now
    stale_re = re.compile(
        "|".join(re.escape(w) for w in cfg.stale_markers), re.IGNORECASE)
    out: list[dict] = []
    for store, root in sorted(cfg.stores.items()):
        root = root.expanduser()
        if not root.is_dir():
            continue
        marker = root / ".last_restored"
        if marker.exists():
            try:
                last = float(marker.read_text().strip() or 0)
            except ValueError:
                last = 0.0
            if (now - last) / 86400 < cfg.freshness_suppress_days:
                continue
        for f in sorted(root.glob("*.md")):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not stale_re.search(text):
                continue
            age_days = int((now - f.stat().st_mtime) / 86400)
            if age_days >= cfg.freshness_stale_days:
                out.append({"store": store, "file": f.name,
                            "age_days": age_days})
    return out


def mark_restored(cfg: Config, store: str, now: float | None = None) -> Path:
    """Record a reconciliation pass for one store."""
    root = cfg.stores[store].expanduser()
    marker = root / ".last_restored"
    marker.write_text(str(int(time.time() if now is None else now)) + "\n",
                      encoding="utf-8")
    return marker
