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


# A store either asserts current state or narrates history, and the difference
# decides whether a stale line in it is a defect.
#
#   index — the store claims to describe how things are now. A line that still
#           carries a stale marker for a fact SHARED_STATE says is resolved is
#           drift, and someone should fix it.
#   log   — an append-only record of past sessions. It is *supposed* to contain
#           statements that were true when written and are false now. Comparing
#           it against live state is a category error, not a detection.
#
# Log-store findings are still reported (under HISTORICAL) but do not count
# toward the drift total that gates a hook.
STORE_KINDS = ("index", "log")
DEFAULT_STORE_KIND = "index"


@dataclass
class Config:
    shared_state: Path = Path("SHARED_STATE.md")
    out_dir: Path = Path("memory_governance")
    stores: dict[str, Path] = field(default_factory=dict)
    store_kinds: dict[str, str] = field(default_factory=dict)
    stale_markers: list[str] = field(default_factory=lambda: list(DEFAULT_STALE_MARKERS))
    resolved_markers: list[str] = field(default_factory=lambda: list(DEFAULT_RESOLVED_MARKERS))
    resolution_words: list[str] = field(default_factory=lambda: list(DEFAULT_RESOLUTION_WORDS))
    freshness_stale_days: int = 2
    freshness_suppress_days: int = 3
    inject_shared_state: bool = True
    max_inject_chars: int = 8000

    def kind_of(self, store: str) -> str:
        return self.store_kinds.get(store, DEFAULT_STORE_KIND)

    @property
    def ledger_path(self) -> Path:
        return self.out_dir / "LEDGER.jsonl"

    @property
    def adjudications_path(self) -> Path:
        return self.out_dir / "ADJUDICATIONS.jsonl"

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

    # A store is either a bare path string, or a table carrying its kind:
    #   codex = "~/.codex/memories"                              -> index
    #   codex = { path = "~/.codex/memories", kind = "log" }     -> log
    for name, value in data.get("stores", {}).items():
        if isinstance(value, dict):
            cfg.stores[name] = _expand(base, value["path"])
            kind = value.get("kind", DEFAULT_STORE_KIND)
            if kind not in STORE_KINDS:
                raise ValueError(
                    f"store {name!r}: kind must be one of {STORE_KINDS}, got {kind!r}")
            cfg.store_kinds[name] = kind
        else:
            cfg.stores[name] = _expand(base, value)

    fresh = data.get("freshness", {})
    if "stale_days" in fresh:
        cfg.freshness_stale_days = int(fresh["stale_days"])
    if "suppress_days" in fresh:
        cfg.freshness_suppress_days = int(fresh["suppress_days"])
    return cfg
