"""Configuration loading for memgov (stdlib-only, TOML)."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_STALE_MARKERS = [
    # English
    "pending", "TBD", "HOLD", "blocked", "unavailable", "not yet",
    "unpushed", "still fails", "is broken", "awaiting", "unreleased",
    # Japanese
    "未実施", "未デポジット", "未生成", "未着手", "未作成", "起動不能",
    "不能", "待ち", "保留", "失敗する",
]
DEFAULT_RESOLVED_MARKERS = [
    "resolved", "published", "fixed", "restored", "repaired", "done",
    "complete", "applied", "live", "operational",
    "済", "復旧", "公開", "正常稼働", "解決", "根治", "完了",
]
DEFAULT_RESOLUTION_WORDS = [
    # words that mark a line as narrating a PAST problem, not a live claim
    "fixed", "resolved", "restored", "repaired", "stale", "corrected",
    "formerly", "previously", "根治", "修理", "復旧", "解決", "修正済",
    "公開済", "完了", "封緘", "陳腐化", "訂正", "旧記載", "当時",
]


@dataclass
class Config:
    shared_state: Path = Path("SHARED_STATE.md")
    out_dir: Path = Path("memory_governance")
    stores: dict[str, Path] = field(default_factory=dict)
    stale_markers: list[str] = field(default_factory=lambda: list(DEFAULT_STALE_MARKERS))
    resolved_markers: list[str] = field(default_factory=lambda: list(DEFAULT_RESOLVED_MARKERS))
    resolution_words: list[str] = field(default_factory=lambda: list(DEFAULT_RESOLUTION_WORDS))
    freshness_stale_days: int = 2
    freshness_suppress_days: int = 3
    inject_shared_state: bool = True
    max_inject_chars: int = 8000

    @property
    def ledger_path(self) -> Path:
        return self.out_dir / "LEDGER.jsonl"

    @property
    def conflict_map_path(self) -> Path:
        return self.out_dir / "CONFLICT_MAP_latest.md"


def _expand(base: Path, value: str) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (base / p)


def load(path: str | Path | None = None) -> Config:
    """Load memgov.toml; missing file yields pure defaults (relative to cwd)."""
    cfg = Config()
    if path is None:
        candidate = Path("memgov.toml")
        path = candidate if candidate.exists() else None
    if path is None:
        return cfg
    path = Path(path)
    base = path.resolve().parent
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    core = data.get("memgov", {})
    if "shared_state" in core:
        cfg.shared_state = _expand(base, core["shared_state"])
    if "out_dir" in core:
        cfg.out_dir = _expand(base, core["out_dir"])
    for key in ("stale_markers", "resolved_markers", "resolution_words"):
        if key in core:
            setattr(cfg, key, list(core[key]))
    for key, attr in (("extra_stale_markers", "stale_markers"),
                      ("extra_resolved_markers", "resolved_markers"),
                      ("extra_resolution_words", "resolution_words")):
        if key in core:
            getattr(cfg, attr).extend(core[key])
    if "inject_shared_state" in core:
        cfg.inject_shared_state = bool(core["inject_shared_state"])
    if "max_inject_chars" in core:
        cfg.max_inject_chars = int(core["max_inject_chars"])

    for name, value in data.get("stores", {}).items():
        cfg.stores[name] = _expand(base, value)

    fresh = data.get("freshness", {})
    if "stale_days" in fresh:
        cfg.freshness_stale_days = int(fresh["stale_days"])
    if "suppress_days" in fresh:
        cfg.freshness_suppress_days = int(fresh["suppress_days"])
    return cfg
